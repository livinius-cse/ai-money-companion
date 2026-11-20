import io
import pytest
from datetime import datetime, timezone
import pypdf
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.models.user import User
from app.services.preflight_qa import PreFlightQAService
from app.services.cover_calculation import CoverCalculationService
from app.core.storage import LocalAssetStorage


def create_blank_pdf_bytes(pages: int, width_pt: float, height_pt: float) -> bytes:
    """Helper to generate a real, valid in-memory multi-page PDF with ReportLab."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width_pt, height_pt))
    for p in range(pages):
        c.drawString(72, height_pt - 72, f"Test Page {p + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


def test_qa_missing_documents_blocks_approval(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Incomplete Book",
        topic="Finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()

    # No chapters, no interior, no cover, no disclosure
    report = PreFlightQAService.run_qa(db_session, book)
    assert report.is_ready_for_approval is False
    assert report.blocking_count > 0

    rule_ids = [f.rule_id for f in report.findings if f.severity == "BLOCKING"]
    assert "QA-MS-001" in rule_ids  # No chapters
    assert "QA-INT-001" in rule_ids  # No interior PDF
    assert "QA-COV-001" in rule_ids  # No cover PDF
    assert "QA-MET-004" in rule_ids  # No AI disclosure


def test_qa_invalid_pdf_blocks_approval(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Invalid PDF Book",
        topic="Finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()

    invalid_pdf = b"%PDF-1.4\nthis is not a valid PDF\n"
    key, size, digest = LocalAssetStorage.save_book_document_file(
        book.id,
        "INTERIOR",
        1,
        invalid_pdf,
    )
    db_session.add(
        BookDocument(
            owner_id=test_user.id,
            book_id=book.id,
            document_type="INTERIOR",
            version=1,
            storage_key=key,
            file_size_bytes=size,
            sha256_hash=digest,
            page_count=1,
            width_pt=432.0,
            height_pt=648.0,
            trim_size="6x9",
            status="GENERATED",
        )
    )
    db_session.commit()

    report = PreFlightQAService.run_qa(db_session, book)
    assert not report.is_ready_for_approval
    assert any(
        finding.category == "INTERIOR" and finding.severity == "BLOCKING"
        for finding in report.findings
    )


def test_qa_paperback_minimum_24_pages(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Thin Book",
        topic="Budgeting",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()

    # Create 10-page interior (violates 24-page minimum for paperback)
    pdf_bytes = create_blank_pdf_bytes(pages=10, width_pt=432.0, height_pt=648.0)
    key, size, sha = LocalAssetStorage.save_book_document_file(book.id, "INTERIOR", 1, pdf_bytes)

    doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        storage_key=key,
        file_size_bytes=size,
        sha256_hash=sha,
        page_count=10,
        width_pt=432.0,
        height_pt=648.0,
        trim_size="6x9",
        status="GENERATED",
    )
    db_session.add(doc)
    db_session.commit()

    report = PreFlightQAService.run_qa(db_session, book)
    finding_24 = next((f for f in report.findings if f.rule_id == "QA-INT-002"), None)
    assert finding_24 is not None
    assert finding_24.severity == "BLOCKING"
    assert "minimum 24 pages" in finding_24.explanation.lower()


def test_qa_even_pages_requirement(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Odd Page Book",
        topic="Investing",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()

    # Create 25-page interior (odd page count)
    pdf_bytes = create_blank_pdf_bytes(pages=25, width_pt=432.0, height_pt=648.0)
    key, size, sha = LocalAssetStorage.save_book_document_file(book.id, "INTERIOR", 1, pdf_bytes)

    doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        storage_key=key,
        file_size_bytes=size,
        sha256_hash=sha,
        page_count=25,
        width_pt=432.0,
        height_pt=648.0,
        trim_size="6x9",
        status="GENERATED",
    )
    db_session.add(doc)
    db_session.commit()

    report = PreFlightQAService.run_qa(db_session, book)
    finding_odd = next((f for f in report.findings if f.rule_id == "QA-INT-003"), None)
    assert finding_odd is not None
    assert finding_odd.severity == "BLOCKING"
    assert "must be even" in finding_odd.explanation.lower()


def test_qa_ready_when_fully_compliant(db_session: Session, test_user: User):
    # 1. Book record
    book = Book(
        owner_id=test_user.id,
        title="Compliant Wealth Blueprint",
        topic="Personal Finance Management and Index Investing",
        book_concept="A tactical manual for financial independence.",
        target_audience="General Adult Readers",
        print_format="paperback",
        marketplace="amazon_com",
        trim_size="6x9",
        paper_type="white_bw",
        target_page_count=24,
    )
    db_session.add(book)
    db_session.commit()

    # 2. Chapters (24 chapters with ample content)
    for i in range(1, 25):
        ch = Chapter(
            book_id=book.id,
            owner_id=test_user.id,
            chapter_number=i,
            title=f"Principle {i}: Capital Preservation and Growth",
            content=f"Detailed chapter {i} content. Building automated cash flow allocation systems. Low fee broad index funds.",
            allocated_pages=1,
            word_count=50,
            draft_status="COMPLETED",
        )
        db_session.add(ch)

    # 3. AI Disclosure
    disclosure = AIDisclosureAttestation(
        user_id=test_user.id,
        disclosure_version="1.0",
        text_creation_method="ai_assisted",
        text_tools_used=["Gemini 1.5 Flash"],
        text_editing_extent="extensive_editing",
        image_creation_method="none",
        image_tools_used=[],
        translation_creation_method="none",
        translation_tools_used=[],
        kdp_submission_declaration="AI tools used for initial drafting with comprehensive human review.",
        author_reviewed=True,
        author_attested_at=datetime.now(timezone.utc),
    )
    db_session.add(disclosure)

    # 4. Compiled 24-page Interior PDF (6x9 = 432x648 pt)
    int_bytes = create_blank_pdf_bytes(pages=24, width_pt=432.0, height_pt=648.0)
    int_key, int_size, int_sha = LocalAssetStorage.save_book_document_file(book.id, "INTERIOR", 1, int_bytes)
    int_doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        storage_key=int_key,
        file_size_bytes=int_size,
        sha256_hash=int_sha,
        page_count=24,
        width_pt=432.0,
        height_pt=648.0,
        trim_size="6x9",
        bleed_config="no_bleed",
        status="GENERATED",
    )
    db_session.add(int_doc)

    # 5. Compiled 1-page Full-Jacket Cover PDF matching calculation
    calc = CoverCalculationService.calculate_full_jacket_cover(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=24,
    )
    cov_bytes = create_blank_pdf_bytes(pages=1, width_pt=calc.full_cover_width_pt, height_pt=calc.full_cover_height_pt)
    cov_key, cov_size, cov_sha = LocalAssetStorage.save_book_document_file(book.id, "COVER", 1, cov_bytes)
    cov_doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="COVER",
        version=1,
        storage_key=cov_key,
        file_size_bytes=cov_size,
        sha256_hash=cov_sha,
        page_count=1,
        width_pt=calc.full_cover_width_pt,
        height_pt=calc.full_cover_height_pt,
        trim_size="6x9",
        status="GENERATED",
    )
    db_session.add(cov_doc)
    db_session.commit()

    # Run QA
    report = PreFlightQAService.run_qa(db_session, book)
    assert report.blocking_count == 0
    assert report.is_ready_for_approval is True
    assert report.hashes.manuscript_hash is not None
    assert report.hashes.metadata_hash is not None
    assert report.hashes.interior_hash is not None
    assert report.hashes.cover_hash is not None
    assert report.hashes.composite_hash is not None
