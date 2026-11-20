import os
import re
import urllib.parse
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.models.book_document import BookDocument
from app.schemas.book_document import (
    InteriorGenerationRequest,
    CoverGenerationRequest,
    BookDocumentResponse,
    BookDocumentListResponse,
    CoverCalculationResponse,
)
from app.services.cover_calculation import CoverCalculationService
from app.services.interior_compiler import InteriorPDFCompiler
from app.services.cover_compiler import FullJacketCoverCompiler
from app.services.quality_validation import QualityValidationService
from app.services.approval import ApprovalService
from app.core.storage import LocalAssetStorage
from app.api.v1.endpoints.books import get_user_book_or_404

router = APIRouter(prefix="/books/{book_id}/documents", tags=["Publishing Documents & PDF Engine"])


def get_user_document_or_404(
    db: Session, book_id: str, document_id: str, user_id: str
) -> BookDocument:
    """Retrieve document record ensuring strict book and owner isolation."""
    doc = db.scalar(
        select(BookDocument).where(
            BookDocument.id == document_id,
            BookDocument.book_id == book_id,
            BookDocument.owner_id == user_id,
        )
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return doc


@router.get("", response_model=BookDocumentListResponse)
def list_book_documents(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all generated interior and cover publishing PDFs for a book."""
    get_user_book_or_404(db, book_id, current_user.id)
    docs = db.scalars(
        select(BookDocument)
        .where(BookDocument.book_id == book_id, BookDocument.owner_id == current_user.id)
        .order_by(desc(BookDocument.created_at))
    ).all()
    return BookDocumentListResponse(items=docs, total=len(docs))


@router.get("/cover-calculator", response_model=CoverCalculationResponse)
def calculate_cover_dimensions(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get deterministic full-jacket cover calculations based on current book specifications
    and rendered interior page count.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)

    # Check if there is a generated interior document to get exact page count
    latest_interior = db.scalar(
        select(BookDocument)
        .where(
            BookDocument.book_id == book_id,
            BookDocument.owner_id == current_user.id,
            BookDocument.document_type == "INTERIOR",
            BookDocument.status == "GENERATED",
        )
        .order_by(desc(BookDocument.version))
    )

    if latest_interior:
        page_count = latest_interior.page_count
        is_provisional = False
        interior_doc_id = latest_interior.id
    else:
        page_count = getattr(book, "target_page_count", 100) or 100
        is_provisional = True
        interior_doc_id = None

    if book.print_format == "hardcover":
        return CoverCalculationService.calculate_hardcover_cover(
            trim_size=book.trim_size,
            paper_type=book.paper_type,
            interior_page_count=page_count,
        )
    else:
        return CoverCalculationService.calculate_paperback_cover(
            trim_size=book.trim_size,
            paper_type=book.paper_type,
            interior_page_count=page_count,
            is_provisional=is_provisional,
            interior_document_id=interior_doc_id,
        )


@router.post("/interior/generate", response_model=BookDocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def generate_interior_pdf(
    book_id: str,
    payload: InteriorGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compile manuscript chapters, front matter, back matter, and approved illustrations
    into an Amazon KDP print-compliant interior PDF.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)

    # Retrieve chapters ordered by chapter_number
    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.book_id == book_id, Chapter.owner_id == current_user.id)
        .order_by(Chapter.chapter_number.asc())
    ).all()

    # Retrieve all illustrations for this book
    illustrations = db.scalars(
        select(Illustration)
        .where(Illustration.book_id == book_id, Illustration.owner_id == current_user.id)
    ).all()

    # Determine next document version
    latest_ver = db.scalar(
        select(func.max(BookDocument.version))
        .where(
            BookDocument.book_id == book_id,
            BookDocument.document_type == "INTERIOR",
            BookDocument.owner_id == current_user.id,
        )
    ) or 0
    next_ver = latest_ver + 1

    try:
        pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
            book=book,
            chapters=chapters,
            illustrations=illustrations,
            req=payload,
        )

        storage_key, size_bytes, sha256 = LocalAssetStorage.save_book_document_file(
            book_id=book_id,
            document_type="INTERIOR",
            version=next_ver,
            file_bytes=pdf_bytes,
        )

        # Run structural validation
        validation = QualityValidationService.validate_pdf_structure(
            pdf_bytes=pdf_bytes,
            document_type="INTERIOR",
            expected_width_pt=meta["page_width_pt"],
            expected_height_pt=meta["page_height_pt"],
            min_pages=24,
        )
        meta["validation_summary"] = validation

        doc_record = BookDocument(
            owner_id=current_user.id,
            book_id=book_id,
            document_type="INTERIOR",
            version=next_ver,
            storage_key=storage_key,
            mime_type="application/pdf",
            file_size_bytes=size_bytes,
            sha256_hash=sha256,
            page_count=meta["final_even_page_count"],
            width_pt=meta["page_width_pt"],
            height_pt=meta["page_height_pt"],
            trim_size=book.trim_size,
            bleed_config=meta["bleed_config"],
            source_book_version=f"v{book.updated_at.strftime('%Y%m%d%H%M%S') if book.updated_at else '1'}",
            generation_metadata=meta,
            status="GENERATED",
        )
        db.add(doc_record)
        ApprovalService.invalidate_active_approval(
            db, book_id, f"Interior PDF regenerated (version {next_ver})", commit=False
        )
        db.commit()
        db.refresh(doc_record)
        return doc_record

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile interior PDF: {str(e)}",
        )


@router.post("/cover/generate", response_model=BookDocumentResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def generate_cover_pdf(
    book_id: str,
    payload: CoverGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an Amazon KDP full-jacket cover PDF with calculated spine, bleed, and safe zones.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)

    # 1. Hardcover honest restriction
    if book.print_format == "hardcover":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hardcover automated standalone cover generation is restricted. Official Amazon KDP template geometry (from https://kdp.amazon.com/en_US/cover-templates) is required to guarantee manufacturing acceptance. Please use Paperback format for verified KDP-ready full-jacket generation.",
        )

    # 2. Determine interior page count - Must use compiled interior document as strict source of truth
    latest_interior = db.scalar(
        select(BookDocument)
        .where(
            BookDocument.book_id == book_id,
            BookDocument.owner_id == current_user.id,
            BookDocument.document_type == "INTERIOR",
            BookDocument.status == "GENERATED",
        )
        .order_by(desc(BookDocument.version))
    )
    if not latest_interior:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate publication cover without a compiled interior PDF. Please compile the interior PDF in Layout Studio first to establish the authoritative physical page count.",
        )

    if latest_interior.page_count < 24:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate publication cover: Compiled interior has only {latest_interior.page_count} pages. Amazon KDP requires a minimum of 24 pages for paperback printing. Please expand manuscript content before generating a cover.",
        )

    page_count = latest_interior.page_count

    calc = CoverCalculationService.calculate_paperback_cover(
        trim_size=book.trim_size,
        paper_type=book.paper_type,
        interior_page_count=page_count,
        is_provisional=False,
        interior_document_id=latest_interior.id,
    )

    # 3. Resolve artwork assets
    front_ill = None
    if payload.front_artwork_id:
        front_ill = db.scalar(
            select(Illustration).where(
                Illustration.id == payload.front_artwork_id,
                Illustration.book_id == book_id,
                Illustration.owner_id == current_user.id,
            )
        )

    back_ill = None
    if payload.back_artwork_id:
        back_ill = db.scalar(
            select(Illustration).where(
                Illustration.id == payload.back_artwork_id,
                Illustration.book_id == book_id,
                Illustration.owner_id == current_user.id,
            )
        )

    latest_ver = db.scalar(
        select(func.max(BookDocument.version))
        .where(
            BookDocument.book_id == book_id,
            BookDocument.document_type == "COVER",
            BookDocument.owner_id == current_user.id,
        )
    ) or 0
    next_ver = latest_ver + 1

    try:
        pdf_bytes, meta = FullJacketCoverCompiler.compile_cover(
            book=book,
            calc=calc,
            req=payload,
            front_ill=front_ill,
            back_ill=back_ill,
        )

        storage_key, size_bytes, sha256 = LocalAssetStorage.save_book_document_file(
            book_id=book_id,
            document_type="COVER",
            version=next_ver,
            file_bytes=pdf_bytes,
        )

        # Run structural validation
        validation = QualityValidationService.validate_pdf_structure(
            pdf_bytes=pdf_bytes,
            document_type="COVER",
            expected_width_pt=calc.full_cover_width_pt,
            expected_height_pt=calc.full_cover_height_pt,
            min_pages=1,
        )
        meta["validation_summary"] = validation

        doc_record = BookDocument(
            owner_id=current_user.id,
            book_id=book_id,
            document_type="COVER",
            version=next_ver,
            storage_key=storage_key,
            mime_type="application/pdf",
            file_size_bytes=size_bytes,
            sha256_hash=sha256,
            page_count=1,
            width_pt=calc.full_cover_width_pt,
            height_pt=calc.full_cover_height_pt,
            trim_size=book.trim_size,
            bleed_config=f"bleed_{calc.bleed_inches}",
            source_book_version=f"v{book.updated_at.strftime('%Y%m%d%H%M%S') if book.updated_at else '1'}",
            generation_metadata=meta,
            status="GENERATED",
        )
        db.add(doc_record)
        ApprovalService.invalidate_active_approval(
            db, book_id, f"Cover PDF regenerated (version {next_ver})", commit=False
        )
        db.commit()
        db.refresh(doc_record)
        return doc_record

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compile full-jacket cover PDF: {str(e)}",
        )


@router.get("/{document_id}", response_model=BookDocumentResponse)
def get_book_document(
    book_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed document metadata and geometry parameters."""
    return get_user_document_or_404(db, book_id, document_id, current_user.id)


@router.api_route("/{document_id}/preview", methods=["GET", "HEAD"])
def preview_book_document(
    book_id: str,
    document_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream PDF document with full RFC 7233 HTTP Byte-Range support (206 Partial Content),
    Content-Range headers, 416 bounds checking, and private no-store caching.
    """
    doc = get_user_document_or_404(db, book_id, document_id, current_user.id)
    file_path = LocalAssetStorage.get_document_path(doc.storage_key)
    file_size = os.path.getsize(file_path)

    range_header = request.headers.get("Range") or request.headers.get("range")

    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, no-cache, no-store, must-revalidate",
        "Content-Type": "application/pdf",
    }

    # HEAD Request support
    if request.method == "HEAD":
        headers["Content-Length"] = str(file_size)
        return Response(status_code=200, headers=headers)

    if not range_header:
        # Full content response (200 OK)
        headers["Content-Length"] = str(file_size)
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            headers=headers,
        )

    # Parse single byte range (e.g. "bytes=0-1023", "bytes=500-", "bytes=-500")
    range_match = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
    if not range_match:
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    start_str, end_str = range_match.groups()
    if not start_str and not end_str:
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    if start_str and not end_str:
        # Suffix range: bytes=500-
        start = int(start_str)
        end = file_size - 1
    elif not start_str and end_str:
        # Last N bytes: bytes=-500
        length = int(end_str)
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        # Closed range: bytes=0-1023
        start = int(start_str)
        end = int(end_str)

    # Validate range bounds
    if start > end or start >= file_size or end >= file_size or start < 0:
        return Response(
            status_code=status.HTTP_416_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_length = end - start + 1
    headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    headers["Content-Length"] = str(chunk_length)

    def iter_file_chunk(path, offset, length, chunk_size=65536):
        with open(path, "rb") as f:
            f.seek(offset)
            remaining = length
            while remaining > 0:
                read_sz = min(remaining, chunk_size)
                data = f.read(read_sz)
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        iter_file_chunk(file_path, start, chunk_length),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )


@router.get("/{document_id}/download")
def download_book_document(
    book_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download the production PDF document as an attachment."""
    book = get_user_book_or_404(db, book_id, current_user.id)
    doc = get_user_document_or_404(db, book_id, document_id, current_user.id)
    file_path = LocalAssetStorage.get_document_path(doc.storage_key)

    clean_title = re.sub(r"[^\w\-_.]", "_", book.title)[:30]
    filename = f"{clean_title}_{doc.document_type.lower()}_v{doc.version}.pdf"
    quoted_filename = urllib.parse.quote(filename)

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{quoted_filename}',
        },
    )


# Dedicated Quality Audit Endpoint for the Book
@router.get("/quality", tags=["Quality & Pre-Flight Validation"])
def get_book_quality_audit(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Comprehensive quality audit across readability, content repetition,
    Amazon policy violations, and structural PDF validation.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)

    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.book_id == book_id, Chapter.owner_id == current_user.id)
        .order_by(Chapter.chapter_number.asc())
    ).all()

    # 1. Full Manuscript Readability
    full_text = " ".join([c.content for c in chapters if c.content])
    readability = QualityValidationService.analyze_readability(full_text, language="en")

    # 2. Content & Amazon Policy Audit
    chap_dicts = [
        {"chapter_number": c.chapter_number, "title": c.title, "content": c.content}
        for c in chapters
    ]
    content_findings = QualityValidationService.audit_manuscript_content(
        book_title=book.title,
        chapters=chap_dicts,
        cover_texts=[book.title, book.subtitle or "", book.topic or ""],
    )

    # 3. Document PDF Inspection Findings
    latest_interior = db.scalar(
        select(BookDocument)
        .where(
            BookDocument.book_id == book_id,
            BookDocument.owner_id == current_user.id,
            BookDocument.document_type == "INTERIOR",
            BookDocument.status == "GENERATED",
        )
        .order_by(desc(BookDocument.version))
    )

    latest_cover = db.scalar(
        select(BookDocument)
        .where(
            BookDocument.book_id == book_id,
            BookDocument.owner_id == current_user.id,
            BookDocument.document_type == "COVER",
            BookDocument.status == "GENERATED",
        )
        .order_by(desc(BookDocument.version))
    )

    pdf_findings = []
    if latest_interior and latest_interior.generation_metadata:
        pdf_findings.extend(
            latest_interior.generation_metadata.get("validation_summary", {}).get("findings", [])
        )
    if latest_cover and latest_cover.generation_metadata:
        pdf_findings.extend(
            latest_cover.generation_metadata.get("validation_summary", {}).get("findings", [])
        )

    all_findings = content_findings + pdf_findings
    blocking_count = sum(1 for f in all_findings if f.get("severity") == "BLOCKING")
    warning_count = sum(1 for f in all_findings if f.get("severity") == "WARNING")
    advisory_count = sum(1 for f in all_findings if f.get("severity") == "ADVISORY")

    return {
        "book_id": book.id,
        "book_title": book.title,
        "readability": readability,
        "findings": all_findings,
        "summary": {
            "total_findings": len(all_findings),
            "blocking": blocking_count,
            "warning": warning_count,
            "advisory": advisory_count,
            "is_preflight_ready": (blocking_count == 0),
        },
        "latest_documents": {
            "interior_version": latest_interior.version if latest_interior else None,
            "cover_version": latest_cover.version if latest_cover else None,
        },
    }
