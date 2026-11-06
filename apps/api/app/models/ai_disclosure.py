import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AIDisclosureAttestation(Base):
    __tablename__ = "ai_disclosure_attestations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    disclosure_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    text_creation_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    text_tools_used: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    text_editing_extent: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        default=None,
    )
    image_creation_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    image_tools_used: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    image_editing_extent: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        default=None,
    )
    translation_creation_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    translation_tools_used: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    translation_editing_extent: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        default=None,
    )
    kdp_submission_declaration: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    author_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    author_attested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AIDisclosureAttestation id={self.id} user_id={self.user_id} reviewed={self.author_reviewed}>"
