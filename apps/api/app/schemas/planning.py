from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChapterPlanItem(BaseModel):
    chapter_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=2, max_length=150)
    summary: str = Field(..., min_length=10, max_length=1000)
    key_takeaways: List[str] = Field(default_factory=list)
    estimated_word_count: int = Field(..., ge=100, le=25000)
    allocated_pages: int = Field(..., ge=1, le=200)


class BookPlanRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    target_audience: str = Field(..., min_length=3, max_length=200)
    book_type: Literal["NON_FICTION", "LOW_CONTENT", "GUIDE"] = "NON_FICTION"
    print_format: Literal["paperback", "hardcover"] = "paperback"
    marketplace: str = Field(default="amazon_com", max_length=30)
    target_trim_size: str = Field(default="6x9", max_length=20)
    paper_type: str = Field(default="white_bw", max_length=30)
    target_pages: int = Field(default=120, ge=1, le=3000, description="Estimated target pages (validated dynamically against selected KDP spec)")


class BookPlanResponse(BaseModel):
    title_options: List[str] = Field(..., min_length=1, max_length=5)
    subtitle_options: List[str] = Field(..., min_length=1, max_length=5)
    target_reader_avatar: str
    front_matter_pages: int = Field(default=4, ge=2)
    chapters: List[ChapterPlanItem]
    back_matter_pages: int = Field(default=2, ge=1)
    total_calculated_pages: int
    is_odd_page_count: bool
    kdp_manufacturing_notice: Optional[str] = None
    specification_matched: bool = True
    spec_id: Optional[str] = None
    specification_advisory: Optional[str] = None
