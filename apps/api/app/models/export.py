import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User
    from app.models.approval import BookApprovalSnapshot


class KDPExportPackage(Base):
    """
    Persistent record of a generated, cryptographically locked Amazon KDP publishing package.
    Packages contain interior.pdf, cover.pdf, kdp_metadata_copysheet.txt,
    ai_disclosure_answers.txt, and manifest.json.
    """
    __tablename__ = "kdp_export_packages"

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
    approval_snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("book_approval_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    export_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    manifest_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    download_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="exports")
    approval_snapshot: Mapped[Optional["BookApprovalSnapshot"]] = relationship(
        "BookApprovalSnapshot"
    )

    def __repr__(self) -> str:
        return f"<KDPExportPackage id={self.id} book_id={self.book_id} version={self.export_version}>"
