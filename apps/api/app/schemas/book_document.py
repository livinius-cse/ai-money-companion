from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class InteriorGenerationRequest(BaseModel):
    include_toc: bool = Field(default=True, description="Generate table of contents with page references")
    include_dedication: bool = Field(default=False, description="Include dedication page in front matter")
    dedication_text: Optional[str] = Field(default=None, max_length=500, description="Optional dedication copy")
    is_full_bleed: bool = Field(default=False, description="Whether paperback interior uses full-bleed")
    font_choice: Literal["serif", "sans"] = Field(default="serif", description="Primary typeface family")
    chapter_header_style: Literal["standard", "minimal", "ornate"] = Field(default="standard")

    model_config = ConfigDict(from_attributes=True)


class CoverGenerationRequest(BaseModel):
    front_artwork_id: Optional[str] = Field(default=None, description="Illustration asset ID for front cover artwork")
    back_artwork_id: Optional[str] = Field(default=None, description="Illustration asset ID for back cover artwork")
    custom_front_title: Optional[str] = Field(default=None, max_length=255)
    custom_front_subtitle: Optional[str] = Field(default=None, max_length=255)
    custom_author_name: Optional[str] = Field(default=None, max_length=255)
    back_cover_description: Optional[str] = Field(default=None, max_length=2000)
    primary_color: str = Field(default="#0f172a", description="Hex background color code")
    accent_color: str = Field(default="#f59e0b", description="Hex accent color code")
    include_spine_text: bool = Field(default=True, description="Attempt spine text if page count >= 80")
    render_guides: bool = Field(default=False, description="Render safe zone and fold line guides for preview")

    model_config = ConfigDict(from_attributes=True)


class BookDocumentResponse(BaseModel):
    id: str
    owner_id: str
    book_id: str
    document_type: str
    version: int
    storage_key: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    page_count: int
    width_pt: float
    height_pt: float
    trim_size: str
    bleed_config: str
    source_book_version: Optional[str] = None
    generation_metadata: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookDocumentListResponse(BaseModel):
    items: List[BookDocumentResponse]
    total: int


class CoverCalculationResponse(BaseModel):
    format: str
    trim_size: str
    paper_type: str
    interior_page_count: int
    even_page_count: int
    spine_coefficient: float
    spine_width_inches: float
    spine_width_pt: float
    full_cover_width_inches: float
    full_cover_width_pt: float
    full_cover_height_inches: float
    full_cover_height_pt: float
    bleed_inches: float
    bleed_pt: float
    safe_zone_margin_inches: float
    safe_zone_margin_pt: float
    spine_text_eligible: bool
    spine_text_reason: Optional[str] = None
    barcode_box: Dict[str, float]
    provenance: str
    is_supported: bool = Field(default=True, description="Whether automated standalone PDF compilation is verified and supported")
    restriction_reason: Optional[str] = Field(default=None, description="Detailed explanation if cover generation is restricted")
    is_provisional: bool = Field(default=False, description="True if calculated without a final compiled interior PDF")
    interior_document_id: Optional[str] = Field(default=None, description="ID of source interior document")
    is_kdp_compliant_page_count: bool = Field(default=True, description="True if interior meets KDP minimum 24-page threshold")
    min_page_warning: Optional[str] = Field(default=None, description="Warning if page count does not satisfy Amazon KDP physical minimums")
