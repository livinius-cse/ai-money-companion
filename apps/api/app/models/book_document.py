import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BookDocument(Base):
    """
    Persistent record for generated interior and cover publishing PDFs.
    Maintains complete version history, geometry metadata, and integrity checksums.
    """
    __tablename__ = "book_documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # "INTERIOR" or "COVER"
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    storage_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
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
    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    width_pt: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    height_pt: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    trim_size: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    bleed_config: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="no_bleed",
    )
    source_book_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )
    generation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )  # "PENDING", "GENERATED", "FAILED"
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    book: Mapped["Book"] = relationship(
        "Book",
        back_populates="documents",
    )

    def __repr__(self) -> str:
        return f"<BookDocument id={self.id} type={self.document_type} v={self.version} status={self.status}>"
