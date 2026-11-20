from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models.book import Book
from app.models.user import User
from app.models.approval import BookApprovalSnapshot
from app.schemas.approval import (
    ApprovalSnapshotResponse,
    ApprovalVerificationResult,
)
from app.services.hasher import CryptographicHasherService
from app.services.preflight_qa import PreFlightQAService


class ApprovalService:
    """
    Service managing cryptographic approval snapshots, explicit owner sign-off,
    dynamic integrity verification, and automatic approval invalidation on mutation.
    """

    @classmethod
    def get_active_approval(
        cls, db: Session, book_id: str, user_id: str
    ) -> Optional[BookApprovalSnapshot]:
        """Fetch the currently active approval snapshot for a book owned by user."""
        return db.scalar(
            select(BookApprovalSnapshot)
            .where(
                BookApprovalSnapshot.book_id == book_id,
                BookApprovalSnapshot.owner_id == user_id,
                BookApprovalSnapshot.status == "ACTIVE",
            )
            .order_by(desc(BookApprovalSnapshot.snapshot_version))
        )

    @classmethod
    def get_approval_history(
        cls, db: Session, book_id: str, user_id: str
    ) -> List[BookApprovalSnapshot]:
        """Fetch all historical approval snapshots for a book, preserving audit trail."""
        return list(
            db.scalars(
                select(BookApprovalSnapshot)
                .where(
                    BookApprovalSnapshot.book_id == book_id,
                    BookApprovalSnapshot.owner_id == user_id,
                )
                .order_by(desc(BookApprovalSnapshot.snapshot_version))
            ).all()
        )

    @classmethod
    def create_approval_snapshot(
        cls,
        db: Session,
        book: Book,
        approving_user: User,
        attestation: str,
    ) -> BookApprovalSnapshot:
        """
        Execute explicit human owner sign-off and persist immutable approval snapshot.
        Fails closed if any blocking QA checks fail or files are corrupt/missing.
        """
        if approving_user.id != book.owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the authenticated book owner can approve this publishing edition.",
            )
        if len(attestation.strip()) < 20:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Approval attestation must contain at least 20 non-whitespace characters.",
            )

        # 1. Run full fresh QA audit
        qa_report = PreFlightQAService.run_qa(db, book)
        if not qa_report.is_ready_for_approval or qa_report.blocking_count > 0:
            blocking_reasons = [
                f"[{f.rule_id}] {f.explanation}"
                for f in qa_report.findings
                if f.severity == "BLOCKING"
            ]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Cannot approve book with active blocking QA failures.",
                    "blocking_count": qa_report.blocking_count,
                    "reasons": blocking_reasons,
                },
            )

        hashes = qa_report.hashes
        if not (
            hashes.manuscript_hash
            and hashes.metadata_hash
            and hashes.interior_hash
            and hashes.cover_hash
            and hashes.composite_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Critical verification failure: Unable to compute all 5 required component hashes.",
            )

        now = datetime.now(timezone.utc)

        # 2. Mark any existing ACTIVE snapshot as SUPERSEDED
        existing_active = db.scalars(
            select(BookApprovalSnapshot).where(
                BookApprovalSnapshot.book_id == book.id,
                BookApprovalSnapshot.owner_id == book.owner_id,
                BookApprovalSnapshot.status == "ACTIVE",
            )
        ).all()
        for snap in existing_active:
            snap.status = "SUPERSEDED"
            snap.invalidated_at = now
            snap.invalidation_reason = "Superseded by newer approval snapshot."

        # 3. Determine next snapshot version
        latest_version = db.scalar(
            select(func.coalesce(func.max(BookApprovalSnapshot.snapshot_version), 0))
            .where(BookApprovalSnapshot.book_id == book.id)
        ) or 0
        next_version = latest_version + 1

        # 4. Create immutable approval snapshot
        snapshot = BookApprovalSnapshot(
            book_id=book.id,
            owner_id=book.owner_id,
            approving_user_id=approving_user.id,
            snapshot_version=next_version,
            status="ACTIVE",
            manuscript_hash=hashes.manuscript_hash,
            metadata_hash=hashes.metadata_hash,
            interior_hash=hashes.interior_hash,
            cover_hash=hashes.cover_hash,
            composite_hash=hashes.composite_hash,
            hash_scheme_version=hashes.hash_scheme_version,
            interior_document_id=qa_report.document_versions.interior_id,
            interior_document_version=qa_report.document_versions.interior_version,
            cover_document_id=qa_report.document_versions.cover_id,
            cover_document_version=qa_report.document_versions.cover_version,
            qa_report_id=qa_report.report_id,
            qa_report_summary=qa_report.model_dump(mode="json"),
            approval_attestation=attestation.strip(),
            created_at=now,
        )

        db.add(snapshot)
        book.status = "APPROVED"
        db.commit()
        db.refresh(snapshot)
        return snapshot

    @classmethod
    def invalidate_active_approval(
        cls,
        db: Session,
        book_id: str,
        reason: str,
        commit: bool = True,
    ) -> Optional[BookApprovalSnapshot]:
        """
        Invalidate active approval snapshot when book contents, illustrations, metadata,
        or compiled documents are mutated. Preserves audit history.
        """
        active = db.scalar(
            select(BookApprovalSnapshot).where(
                BookApprovalSnapshot.book_id == book_id,
                BookApprovalSnapshot.status == "ACTIVE",
            )
        )
        if not active:
            return None

        now = datetime.now(timezone.utc)
        active.status = "INVALIDATED"
        active.invalidated_at = now
        active.invalidation_reason = reason

        book = db.scalar(select(Book).where(Book.id == book_id))
        if book and book.status == "APPROVED":
            book.status = "IN_PROGRESS"

        if commit:
            db.commit()
            db.refresh(active)
        return active

    @classmethod
    def verify_approval_integrity(
        cls,
        db: Session,
        book: Book,
    ) -> ApprovalVerificationResult:
        """
        Recalculates all five current hashes and strictly verifies that the active approval
        snapshot still matches current stored disk bytes, manuscript, and metadata.
        If any divergence is detected, invalidates active approval immediately.
        """
        active = cls.get_active_approval(db, book.id, book.owner_id)
        current_data = CryptographicHasherService.compute_all_hashes(db, book)

        current_hashes_dict = {
            "manuscript_hash": current_data.get("manuscript_hash"),
            "metadata_hash": current_data.get("metadata_hash"),
            "interior_hash": current_data.get("interior_hash"),
            "cover_hash": current_data.get("cover_hash"),
            "composite_hash": current_data.get("composite_hash"),
        }

        if not active:
            return ApprovalVerificationResult(
                is_valid=False,
                active_snapshot=None,
                hash_match=False,
                current_hashes=current_hashes_dict,
                divergences=["No active human approval snapshot exists for this book."],
                remediation="Run Pre-Flight QA and perform explicit owner sign-off.",
            )

        divergences: List[str] = []
        if active.hash_scheme_version != current_data.get("hash_scheme_version"):
            divergences.append("The approval uses a different cryptographic hash scheme.")
        if active.manuscript_hash != current_hashes_dict["manuscript_hash"]:
            divergences.append("Manuscript or approved illustration content has changed since approval.")
        if active.metadata_hash != current_hashes_dict["metadata_hash"]:
            divergences.append("KDP metadata or publishing parameters have changed since approval.")
        if active.interior_hash != current_hashes_dict["interior_hash"]:
            divergences.append("Interior PDF document has changed or been recompiled since approval.")
        if active.cover_hash != current_hashes_dict["cover_hash"]:
            divergences.append("Cover PDF document has changed or been recompiled since approval.")
        if active.composite_hash != current_hashes_dict["composite_hash"]:
            divergences.append("Composite cryptographic manifest hash mismatch.")

        # Check document ID / version match
        interior_doc = current_data.get("interior_document")
        if not interior_doc or not active.interior_document_id:
            divergences.append("The approved interior document is missing.")
        elif interior_doc.id != active.interior_document_id:
            divergences.append(f"Interior document ID mismatch: approved {active.interior_document_id}, current {interior_doc.id}.")
        elif interior_doc.version != active.interior_document_version:
            divergences.append(
                f"Interior document version mismatch: approved {active.interior_document_version}, current {interior_doc.version}."
            )
        cover_doc = current_data.get("cover_document")
        if not cover_doc or not active.cover_document_id:
            divergences.append("The approved cover document is missing.")
        elif cover_doc.id != active.cover_document_id:
            divergences.append(f"Cover document ID mismatch: approved {active.cover_document_id}, current {cover_doc.id}.")
        elif cover_doc.version != active.cover_document_version:
            divergences.append(
                f"Cover document version mismatch: approved {active.cover_document_version}, current {cover_doc.version}."
            )

        if divergences:
            # Invalidate snapshot due to verified divergence
            reason = f"Cryptographic divergence detected: {'; '.join(divergences)}"
            cls.invalidate_active_approval(db, book.id, reason)

            return ApprovalVerificationResult(
                is_valid=False,
                active_snapshot=ApprovalSnapshotResponse.model_validate(active),
                hash_match=False,
                current_hashes=current_hashes_dict,
                divergences=divergences,
                remediation="Re-run Pre-Flight QA and provide fresh owner sign-off.",
            )

        return ApprovalVerificationResult(
            is_valid=True,
            active_snapshot=ApprovalSnapshotResponse.model_validate(active),
            hash_match=True,
            current_hashes=current_hashes_dict,
            divergences=[],
            remediation=None,
        )
