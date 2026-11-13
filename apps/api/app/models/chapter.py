import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.illustration import Illustration


class Chapter(Base):
    __tablename__ = "chapters"

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
    chapter_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    chapter_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="chapter",
    )  # "front_matter", "chapter", "back_matter"
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )  # Markdown manuscript content
    allocated_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    draft_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="NOT_STARTED",
    )  # "NOT_STARTED", "DRAFT", "IN_PROGRESS", "COMPLETED"
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
        back_populates="chapters",
    )
    illustrations: Mapped[List["Illustration"]] = relationship(
        "Illustration",
        back_populates="chapter",
    )

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} num={self.chapter_number} title={self.title}>"
