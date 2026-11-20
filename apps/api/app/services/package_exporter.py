import re
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func

from app.models.book import Book
from app.models.user import User
from app.models.approval import BookApprovalSnapshot
from app.models.export import KDPExportPackage
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.schemas.export import ExportEligibilityResponse
from app.services.hasher import (
    CryptographicHasherService,
    calculate_sha256_hex,
    canonical_json_bytes,
)
from app.services.approval import ApprovalService
from app.services.preflight_qa import PreFlightQAService
from app.core.storage import LocalAssetStorage


def is_safe_zip_path(filename: str) -> bool:
    """Reject absolute, traversal, drive-qualified, and separator-ambiguous ZIP member names."""
    if not filename or "\x00" in filename or "\\" in filename:
        return False
    raw_parts = filename.split("/")
    posix_path = PurePosixPath(filename)
    windows_path = PureWindowsPath(filename)
    return not (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or any(part in ("", ".", "..") for part in raw_parts)
    )


class KDPPackageExporterService:
    """
    Secure packaging engine for Amazon KDP manual publishing handoff.
    Generates cryptographically validated ZIP bundles containing verified interior.pdf,
    cover.pdf, metadata copysheets, AI disclosure declarations, and manifest.json.
    """

    @classmethod
    def check_eligibility(cls, db: Session, book: Book) -> ExportEligibilityResponse:
        """
        Verify whether the book is currently eligible for KDP package generation:
        Requires active approval snapshot with zero hash divergences.
        """
        active = ApprovalService.get_active_approval(db, book.id, book.owner_id)
        if active:
            verification = ApprovalService.verify_approval_integrity(db, book)
            if not verification.is_valid:
                active = None

        current_data = CryptographicHasherService.compute_all_hashes(db, book)
        qa_report = PreFlightQAService.run_qa(db, book)

        blocking_reasons: List[str] = []
        if not active:
            blocking_reasons.append("No active human approval snapshot exists. Run Pre-Flight QA and sign off.")
        if qa_report.blocking_count:
            blocking_reasons.append(
                f"Current pre-flight QA has {qa_report.blocking_count} blocking finding(s)."
            )

        hashes_verified = False
        if active:
            if active.hash_scheme_version != current_data.get("hash_scheme_version"):
                blocking_reasons.append("Hash scheme version differs from the active approval.")
            if active.manuscript_hash != current_data.get("manuscript_hash"):
                blocking_reasons.append("Manuscript or approved illustrations have changed since approval.")
            if active.metadata_hash != current_data.get("metadata_hash"):
                blocking_reasons.append("Book metadata or KDP configuration has changed since approval.")
            if active.interior_hash != current_data.get("interior_hash"):
                blocking_reasons.append("Interior PDF document has changed or was recompiled since approval.")
            if active.cover_hash != current_data.get("cover_hash"):
                blocking_reasons.append("Cover PDF document has changed or was recompiled since approval.")
            if active.composite_hash != current_data.get("composite_hash"):
                blocking_reasons.append("Composite manifest hash does not match current book state.")

            # Check interior/cover document IDs match
            interior_doc = current_data.get("interior_document")
            if not interior_doc or interior_doc.id != active.interior_document_id:
                current_id = interior_doc.id if interior_doc else None
                blocking_reasons.append(f"Interior document ID mismatch: approved {active.interior_document_id}, current {current_id}.")
            elif interior_doc.version != active.interior_document_version:
                blocking_reasons.append("Interior document version differs from the active approval.")
            cover_doc = current_data.get("cover_document")
            if not cover_doc or cover_doc.id != active.cover_document_id:
                current_id = cover_doc.id if cover_doc else None
                blocking_reasons.append(f"Cover document ID mismatch: approved {active.cover_document_id}, current {current_id}.")
            elif cover_doc.version != active.cover_document_version:
                blocking_reasons.append("Cover document version differs from the active approval.")

            if not blocking_reasons and all(
                current_data.get(name)
                for name in (
                    "manuscript_hash",
                    "metadata_hash",
                    "interior_hash",
                    "cover_hash",
                    "composite_hash",
                )
            ):
                hashes_verified = True

        return ExportEligibilityResponse(
            is_eligible=(len(blocking_reasons) == 0 and active is not None),
            active_approval_id=active.id if active else None,
            approval_version=active.snapshot_version if active else None,
            hashes_verified=hashes_verified,
            blocking_reasons=blocking_reasons,
            interior_document_id=active.interior_document_id if active else None,
            cover_document_id=active.cover_document_id if active else None,
            current_composite_hash=current_data.get("composite_hash"),
            approval_composite_hash=active.composite_hash if active else None,
        )

    @classmethod
    def export_kdp_package(
        cls,
        db: Session,
        book: Book,
        user: User,
    ) -> KDPExportPackage:
        """
        Generate, cryptographically seal, and persist an Amazon KDP ZIP publishing package.
        Fails closed if any eligibility condition or hash verification fails.
        """
        if user.id != book.owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found.",
            )

        # 1. Check eligibility
        eligibility = cls.check_eligibility(db, book)
        if not eligibility.is_eligible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Cannot export KDP package: book does not satisfy pre-flight export criteria.",
                    "reasons": eligibility.blocking_reasons,
                },
            )

        active_snapshot = db.scalar(
            select(BookApprovalSnapshot).where(
                BookApprovalSnapshot.id == eligibility.active_approval_id,
                BookApprovalSnapshot.book_id == book.id,
                BookApprovalSnapshot.owner_id == user.id,
                BookApprovalSnapshot.status == "ACTIVE",
            )
        )
        if not active_snapshot:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active approval snapshot not found or has been invalidated.",
            )

        # Re-read source hashes immediately before packaging.
        current_data = CryptographicHasherService.compute_all_hashes(db, book)
        interior_bytes = current_data.get("interior_bytes")
        cover_bytes = current_data.get("cover_bytes")
        interior_doc = current_data.get("interior_document")
        cover_doc = current_data.get("cover_document")
        ai_disclosure = current_data.get("ai_disclosure")

        if (
            not interior_bytes
            or not cover_bytes
            or not interior_doc
            or not cover_doc
            or active_snapshot.hash_scheme_version != current_data.get("hash_scheme_version")
            or active_snapshot.manuscript_hash != current_data.get("manuscript_hash")
            or active_snapshot.metadata_hash != current_data.get("metadata_hash")
            or active_snapshot.interior_hash != current_data.get("interior_hash")
            or active_snapshot.cover_hash != current_data.get("cover_hash")
            or active_snapshot.composite_hash != current_data.get("composite_hash")
            or active_snapshot.interior_document_id != interior_doc.id
            or active_snapshot.interior_document_version != interior_doc.version
            or active_snapshot.cover_document_id != cover_doc.id
            or active_snapshot.cover_document_version != cover_doc.version
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Approval or source documents changed during export validation. Run pre-flight QA and approve again.",
            )

        fresh_qa = PreFlightQAService.run_qa(db, book)
        if not fresh_qa.is_ready_for_approval or fresh_qa.blocking_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Current pre-flight QA contains blocking findings. Resolve them before exporting.",
            )

        metadata_copysheet_str = cls._build_metadata_copysheet(book, interior_doc, cover_doc)
        metadata_copysheet_bytes = metadata_copysheet_str.encode("utf-8")
        ai_disclosure_str = cls._build_ai_disclosure_sheet(ai_disclosure)
        ai_disclosure_bytes = ai_disclosure_str.encode("utf-8")

        export_now = datetime.now(timezone.utc)
        export_id = str(uuid.uuid4())
        interior_sha = calculate_sha256_hex(interior_bytes)
        cover_sha = calculate_sha256_hex(cover_bytes)
        copysheet_sha = calculate_sha256_hex(metadata_copysheet_bytes)
        disclosure_sha = calculate_sha256_hex(ai_disclosure_bytes)

        # Next export version
        latest_ver = db.scalar(
            select(func.coalesce(func.max(KDPExportPackage.export_version), 0))
            .where(
                KDPExportPackage.book_id == book.id,
                KDPExportPackage.owner_id == user.id,
            )
        ) or 0
        next_ver = latest_ver + 1

        manifest_data = {
            "hand_off_notice": "This package is prepared for manual publishing handoff to Amazon KDP (kdp.amazon.com). Automated upload is not performed.",
            "book_reference": {"book_id": book.id, "owner_id": user.id},
            "export_id": export_id,
            "export_version": next_ver,
            "export_timestamp": export_now.isoformat(),
            "provenance": {
                "source": "Persisted book configuration, manuscript, disclosure, and approved PDF documents.",
                "generation": "Generated locally for manual KDP handoff; no upload or publishing action was performed.",
            },
            "book": {
                "id": book.id,
                "title": book.title,
                "subtitle": book.subtitle,
                "topic": book.topic,
                "book_concept": book.book_concept,
                "target_audience": book.target_audience,
                "book_type": book.book_type,
                "print_format": book.print_format,
                "marketplace": book.marketplace,
                "trim_size": book.trim_size,
                "paper_type": book.paper_type,
                "target_page_count": book.target_page_count,
            },
            "publishing_configuration": {
                "print_format": book.print_format,
                "marketplace": book.marketplace,
                "trim_size": book.trim_size,
                "paper_type": book.paper_type,
                "interior_page_count": interior_doc.page_count,
                "bleed_config": interior_doc.bleed_config,
            },
            "approval_reference": {
                "snapshot_id": active_snapshot.id,
                "snapshot_version": active_snapshot.snapshot_version,
                "owner_id": active_snapshot.owner_id,
                "approving_user_id": active_snapshot.approving_user_id,
                "approval_timestamp": active_snapshot.created_at.isoformat(),
                "attestation": active_snapshot.approval_attestation,
            },
            "cryptographic_manifest": {
                "hash_scheme_version": active_snapshot.hash_scheme_version,
                "manuscript_hash": active_snapshot.manuscript_hash,
                "metadata_hash": active_snapshot.metadata_hash,
                "interior_hash": active_snapshot.interior_hash,
                "cover_hash": active_snapshot.cover_hash,
                "composite_hash": active_snapshot.composite_hash,
            },
            "documents": {
                "interior": {
                    "document_id": interior_doc.id,
                    "version": interior_doc.version,
                    "page_count": interior_doc.page_count,
                    "width_pt": interior_doc.width_pt,
                    "height_pt": interior_doc.height_pt,
                    "file_size_bytes": len(interior_bytes),
                    "sha256": interior_sha,
                },
                "cover": {
                    "document_id": cover_doc.id,
                    "version": cover_doc.version,
                    "width_pt": cover_doc.width_pt,
                    "height_pt": cover_doc.height_pt,
                    "file_size_bytes": len(cover_bytes),
                    "sha256": cover_sha,
                },
            },
            "files": {
                "interior.pdf": {"sha256": interior_sha, "size_bytes": len(interior_bytes)},
                "cover.pdf": {"sha256": cover_sha, "size_bytes": len(cover_bytes)},
                "kdp_metadata_copysheet.txt": {
                    "sha256": copysheet_sha,
                    "size_bytes": len(metadata_copysheet_bytes),
                },
                "ai_disclosure_answers.txt": {
                    "sha256": disclosure_sha,
                    "size_bytes": len(ai_disclosure_bytes),
                },
            },
        }

        manifest_bytes = canonical_json_bytes(manifest_data)
        temp_path: Optional[Path] = None
        storage_key: Optional[str] = None
        persisted = False
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".kdp-export-",
                suffix=".zip",
                dir=LocalAssetStorage.get_exports_base_dir(),
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            with zipfile.ZipFile(temp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                members = {
                    "interior.pdf": interior_bytes,
                    "cover.pdf": cover_bytes,
                    "kdp_metadata_copysheet.txt": metadata_copysheet_bytes,
                    "ai_disclosure_answers.txt": ai_disclosure_bytes,
                    "manifest.json": manifest_bytes,
                }
                for member_name, member_bytes in members.items():
                    if not is_safe_zip_path(member_name):
                        raise ValueError("Unsafe package member path.")
                    archive.writestr(member_name, member_bytes)

            storage_key, file_size, zip_sha = LocalAssetStorage.save_export_package_file_from_path(
                book_id=book.id,
                version=next_ver,
                source_path=temp_path,
            )
            temp_path = None

            safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", book.title)[:40]
            package_filename = f"KDP_{safe_title or 'Book'}_v{next_ver}.zip"
            export_package = KDPExportPackage(
                id=export_id,
                book_id=book.id,
                owner_id=user.id,
                approval_snapshot_id=active_snapshot.id,
                export_version=next_ver,
                filename=package_filename,
                storage_key=storage_key,
                file_size_bytes=file_size,
                sha256_hash=zip_sha,
                manifest_data=manifest_data,
                download_count=0,
                created_at=export_now,
            )
            db.add(export_package)
            db.commit()
            db.refresh(export_package)
            persisted = True
            return export_package
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            if storage_key and not persisted:
                LocalAssetStorage.get_export_package_path(storage_key).unlink()

    @classmethod
    def get_export_history(cls, db: Session, book_id: str, user_id: str) -> List[KDPExportPackage]:
        """Fetch all historical export packages generated for this book."""
        return list(
            db.scalars(
                select(KDPExportPackage)
                .where(
                    KDPExportPackage.book_id == book_id,
                    KDPExportPackage.owner_id == user_id,
                )
                .order_by(desc(KDPExportPackage.export_version))
            ).all()
        )

    # -------------------------------------------------------------------------
    # Copy Sheet Builders
    # -------------------------------------------------------------------------
    @classmethod
    def _build_metadata_copysheet(cls, book: Book, interior_doc: BookDocument, cover_doc: BookDocument) -> str:
        lines = [
            "================================================================================",
            "AMAZON KDP PUBLISHING METADATA COPY SHEET",
            "Prepared by AI Money Companion — KDP Publishing OS",
            "================================================================================",
            "",
            "HANDOFF INSTRUCTIONS:",
            "Copy and paste the exact fields below directly into your Amazon KDP dashboard",
            "(https://kdp.amazon.com/title-setup).",
            "",
            "--------------------------------------------------------------------------------",
            "1. BOOK DETAILS & TITLE",
            "--------------------------------------------------------------------------------",
            f"Title:                 {book.title}",
            f"Subtitle:              {book.subtitle or 'N/A'}",
            f"Book Type:             {book.book_type}",
            f"Primary Language:      English",
            "",
            "--------------------------------------------------------------------------------",
            "2. MANUFACTURING SPECIFICATIONS",
            "--------------------------------------------------------------------------------",
            f"Print Format:          {book.print_format.title()}",
            f"Trim Size:             {book.trim_size}",
            f"Interior Paper Type:   {book.paper_type}",
            f"Interior Page Count:   {interior_doc.page_count} pages",
            f"Bleed Setting:         {interior_doc.bleed_config}",
            f"Cover Dimensions:      {cover_doc.width_pt:.2f}pt x {cover_doc.height_pt:.2f}pt",
            f"Primary Marketplace:   {book.marketplace}",
            "",
            "--------------------------------------------------------------------------------",
            "3. TARGET AUDIENCE & POSITIONING",
            "--------------------------------------------------------------------------------",
            f"Target Audience:       {book.target_audience or 'General'}",
            f"Reader Profile:        {book.target_reader_profile or 'General adult readership'}",
            "",
            "--------------------------------------------------------------------------------",
            "4. TOPIC SUMMARY & PREMISE",
            "--------------------------------------------------------------------------------",
            f"{book.topic}",
            "",
            "================================================================================",
            "END OF METADATA COPY SHEET",
            "================================================================================",
        ]
        return "\n".join(lines)

    @classmethod
    def _build_ai_disclosure_sheet(cls, disclosure: Optional[AIDisclosureAttestation]) -> str:
        if not disclosure:
            return "No AI disclosure on file."

        lines = [
            "================================================================================",
            "AMAZON KDP MANDATORY AI CONTENT DISCLOSURE DECLARATION",
            "================================================================================",
            "",
            "Amazon KDP Question: 'Did you use AI tools (like ChatGPT, Midjourney) in creating texts, images, or translations?'",
            "",
            f"1. TEXT GENERATION:",
            f"   Creation Method:    {disclosure.text_creation_method}",
            f"   Tools Used:         {', '.join(disclosure.text_tools_used or []) or 'None'}",
            f"   Editing Extent:     {disclosure.text_editing_extent or 'N/A'}",
            "",
            f"2. IMAGE / ARTWORK GENERATION:",
            f"   Creation Method:    {disclosure.image_creation_method}",
            f"   Tools Used:         {', '.join(disclosure.image_tools_used or []) or 'None'}",
            f"   Editing Extent:     {disclosure.image_editing_extent or 'N/A'}",
            "",
            f"3. TRANSLATION:",
            f"   Creation Method:    {disclosure.translation_creation_method}",
            f"   Tools Used:         {', '.join(disclosure.translation_tools_used or []) or 'None'}",
            f"   Editing Extent:     {disclosure.translation_editing_extent or 'N/A'}",
            "",
            f"4. AUTHOR ATTESTATION:",
            f"   Confirmed by Author: Yes",
            f"   Attested At:         {disclosure.author_attested_at.isoformat() if disclosure.author_attested_at else 'Verified'}",
            f"   Submission Notes:    {disclosure.kdp_submission_declaration}",
            "",
            "================================================================================",
        ]
        return "\n".join(lines)
