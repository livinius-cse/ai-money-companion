import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class SalesImportBatch(Base):
    """
    Audit record for user-uploaded Amazon KDP sales reports (CSV/XLSX) or simulated demo seeds.
    Tracks file provenance (REAL_KDP_REPORT vs SIMULATED_DEMO), source hash, and row counts.
    """
    __tablename__ = "sales_import_batches"
    __table_args__ = (
        Index(
            "uq_sales_import_source",
            "owner_id",
            "book_id",
            "report_type",
            "provenance",
            "source_sha256",
            unique=True,
        ),
    )

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
    book_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sanitized_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LEGACY",
        index=True,
    )
    source_headers: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
    )
    column_mapping: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON,
        nullable=True,
    )
    reporting_period: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )  # e.g., "2026-03" or "2026-Q1"
    marketplace: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    currency: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    source_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    provenance: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REAL_KDP_REPORT",
    )  # "REAL_KDP_REPORT" or "SIMULATED_DEMO"
    validation_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="VALID",
    )  # "VALID", "INVALID", "PROCESSED"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    records: Mapped[List["SalesRecord"]] = relationship(
        "SalesRecord",
        back_populates="batch",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SalesImportBatch id={self.id} provenance={self.provenance} rows={self.row_count}>"


class SalesRecord(Base):
    """
    Granular transaction record imported from an Amazon KDP Monthly Royalties/Orders report.
    Strictly isolated by owner and provenance (real reports are never mixed with demo data).
    """
    __tablename__ = "sales_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sales_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    book_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("books.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_date: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )  # "YYYY-MM-DD"
    asin_isbn: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    marketplace: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    format: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        default=None,
    )  # "Paperback", "Hardcover", "eBook"
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="LEGACY",
        index=True,
    )
    paid_units: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    free_units: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    kenp_read_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    units_sold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    units_refunded: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    net_units: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    currency: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )  # e.g., "USD", "GBP", "EUR"
    royalty_amount: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    provenance: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REAL_KDP_REPORT",
        index=True,
    )  # "REAL_KDP_REPORT" or "SIMULATED_DEMO"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    batch: Mapped["SalesImportBatch"] = relationship(
        "SalesImportBatch",
        back_populates="records",
    )

    def __repr__(self) -> str:
        return f"<SalesRecord id={self.id} title={self.title} units={self.net_units} {self.currency}>"
