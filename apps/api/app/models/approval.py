import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BookApprovalSnapshot(Base):
    """
    Immutable human approval snapshot representing an explicit cryptographic gate
    before Amazon KDP package export.
    Stores deterministic component hashes, composite hash, document versions,
    QA report findings snapshot, approving user reference, and sign-off attestation.
    """
    __tablename__ = "book_approval_snapshots"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approving_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="ACTIVE",
    )  # "ACTIVE", "INVALIDATED", "SUPERSEDED"

    # Deterministic SHA-256 Hashes
    manuscript_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    metadata_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    interior_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    cover_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    composite_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    hash_scheme_version: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="kdp-sha256-v1",
    )

    # Document references at time of approval
    interior_document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        default=None,
    )
    interior_document_version: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )
    cover_document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        default=None,
    )
    cover_document_version: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )

    # QA Audit Reference and Snapshot
    qa_report_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        default=None,
    )
    qa_report_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )

    # Explicit human sign-off attestation
    approval_attestation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Timestamps & Invalidation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    invalidation_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    # Relationships
    book: Mapped["Book"] = relationship(
        "Book",
        back_populates="approvals",
    )
    approving_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[approving_user_id],
    )

    def __repr__(self) -> str:
        return f"<BookApprovalSnapshot id={self.id} book_id={self.book_id} version={self.snapshot_version} status={self.status}>"
