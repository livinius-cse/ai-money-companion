from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SystemState(Base):
    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        index=True,
    )
    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemState {self.key}={self.value}>"
