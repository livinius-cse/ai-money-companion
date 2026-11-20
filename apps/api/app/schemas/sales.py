from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SalesProvenance = Literal["REAL_KDP_REPORT", "SIMULATED_DEMO"]
SalesReportType = Literal["ORDERS", "KENP_READ", "PRIOR_MONTH_ROYALTIES"]


class SalesImportField(BaseModel):
    key: str
    label: str
    required: bool


class SalesImportPreviewResponse(BaseModel):
    source_sha256: str
    report_type: SalesReportType
    provenance: SalesProvenance
    source_headers: List[str]
    fields: List[SalesImportField]
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    source_preview: List[Dict[str, Optional[str]]] = Field(default_factory=list)
    mapped_preview: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int
    validation_errors: List[str] = Field(default_factory=list)
    can_import: bool


class SalesImportBatchResponse(BaseModel):
    id: str
    owner_id: str
    book_id: Optional[str] = None
    original_filename: str
    sanitized_filename: str
    report_type: str
    source_headers: Optional[List[str]] = None
    column_mapping: Optional[Dict[str, str]] = None
    reporting_period: Optional[str] = None
    marketplace: Optional[str] = None
    currency: Optional[str] = None
    source_sha256: str
    row_count: int
    provenance: SalesProvenance
    validation_result: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesImportBatchListResponse(BaseModel):
    items: List[SalesImportBatchResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class SalesRecordResponse(BaseModel):
    id: str
    batch_id: str
    owner_id: str
    book_id: Optional[str] = None
    report_type: str
    transaction_date: str
    asin_isbn: Optional[str] = None
    title: str
    author: Optional[str] = None
    marketplace: str
    format: Optional[str] = None
    paid_units: int
    free_units: int
    kenp_read_pages: int
    currency: Optional[str] = None
    royalty_amount: Optional[float] = None
    provenance: SalesProvenance
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrencyBreakdown(BaseModel):
    currency: str
    reported_royalties: float


class MarketplaceBreakdown(BaseModel):
    marketplace: str
    paid_units: int
    free_units: int
    kenp_read_pages: int
    royalties_by_currency: Dict[str, float]


class FormatBreakdown(BaseModel):
    format: Optional[str] = None
    paid_units: int
    free_units: int


class SalesAnalyticsSummary(BaseModel):
    report_type: SalesReportType
    provenance: SalesProvenance
    is_demo: bool
    demo_disclaimer: Optional[str] = None
    total_paid_units: int
    total_free_units: int
    total_kenp_read_pages: int
    transaction_count: int
    batch_count: int
    royalty_totals: List[CurrencyBreakdown]
    marketplace_breakdown: List[MarketplaceBreakdown]
    format_breakdown: List[FormatBreakdown]
    reporting_periods: List[str]
    earliest_date: Optional[str] = None
    latest_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
