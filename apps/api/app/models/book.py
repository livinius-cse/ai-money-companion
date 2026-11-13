import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.illustration import Illustration
    from app.models.user import User


class Book(Base):
    __tablename__ = "books"

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
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    subtitle: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    topic: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    book_concept: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    target_audience: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
    )
    target_reader_profile: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    book_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="non_fiction",
    )
    print_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="paperback",
    )
    marketplace: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="amazon_com",
    )
    trim_size: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="6x9",
    )
    paper_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="white_bw",
    )
    target_page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
    )
    front_matter_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
    )
    back_matter_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
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
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_number",
    )
    illustrations: Mapped[List["Illustration"]] = relationship(
        "Illustration",
        back_populates="book",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title} status={self.status}>"
