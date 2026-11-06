from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class RuleViolation(BaseModel):
    rule_id: str
    field: str
    severity: Literal["BLOCKING_ERROR", "ADVISORY_WARNING"]
    message: str
    reference_doc: str


class PrintSpecsValidationRequest(BaseModel):
    print_format: Literal["paperback", "hardcover"] = "paperback"
    trim_size: str = Field(default="6x9", description="Trim size string, e.g. '6x9', '8.5x11'")
    paper_type: str = Field(default="white_bw", description="Paper and ink option, e.g. 'white_bw', 'cream_bw', 'groundwood_bw', 'standard_color', 'premium_color'")
    page_count: int = Field(..., ge=1, le=5000, description="Total planned manuscript page count")
    has_bleed: bool = Field(default=False)
    inside_margin_in: Optional[float] = Field(default=None, description="Actual inside/gutter margin in inches")
    outside_margin_in: Optional[float] = Field(default=None, description="Actual outside margin in inches")
    marketplace: str = Field(default="amazon_com")


class MetadataValidationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    subtitle: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    description_html: str = Field(default="")


class ValidationResultResponse(BaseModel):
    is_valid: bool
    blocking_errors: List[RuleViolation] = Field(default_factory=list)
    advisory_warnings: List[RuleViolation] = Field(default_factory=list)
    applicable_page_count: int
    calculated_spine_width_in: Optional[float] = None
    spine_text_allowed: bool = False
    matched_specification: Optional[Dict[str, Any]] = None
