from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Book main title")
    subtitle: Optional[str] = Field(default=None, max_length=255, description="Optional book subtitle")
    topic: str = Field(..., min_length=1, description="Core topic or niche of the book")
    book_concept: Optional[str] = Field(default=None, description="Detailed concept and premise")
    target_audience: Optional[str] = Field(default=None, max_length=255, description="Primary audience")
    target_reader_profile: Optional[str] = Field(default=None, description="Reader persona/avatar description")
    book_type: Literal["non_fiction", "fiction", "workbook", "journal"] = "non_fiction"
    print_format: Literal["paperback", "hardcover"] = "paperback"
    marketplace: str = Field(default="amazon_com", max_length=50)
    trim_size: str = Field(default="6x9", max_length=30)
    paper_type: str = Field(default="white_bw", max_length=50)
    target_page_count: int = Field(default=100, ge=24, le=1000)

    model_config = ConfigDict(from_attributes=True)


class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    subtitle: Optional[str] = Field(default=None, max_length=255)
    topic: Optional[str] = Field(default=None, min_length=1)
    book_concept: Optional[str] = None
    target_audience: Optional[str] = Field(default=None, max_length=255)
    target_reader_profile: Optional[str] = None
    book_type: Optional[str] = None
    print_format: Optional[str] = None
    marketplace: Optional[str] = None
    trim_size: Optional[str] = None
    paper_type: Optional[str] = None
    target_page_count: Optional[int] = Field(default=None, ge=24, le=1000)
    status: Optional[str] = None
    front_matter_pages: Optional[int] = Field(default=None, ge=0, le=100)
    back_matter_pages: Optional[int] = Field(default=None, ge=0, le=100)

    model_config = ConfigDict(from_attributes=True)


class BookResponse(BaseModel):
    id: str
    owner_id: str
    title: str
    subtitle: Optional[str] = None
    topic: str
    book_concept: Optional[str] = None
    target_audience: Optional[str] = None
    target_reader_profile: Optional[str] = None
    book_type: str
    print_format: str
    marketplace: str
    trim_size: str
    paper_type: str
    target_page_count: int
    status: str
    front_matter_pages: int
    back_matter_pages: int
    created_at: datetime
    updated_at: datetime

    # Computed aggregates
    chapter_count: int = 0
    total_allocated_pages: int = 0
    total_word_count: int = 0
    illustration_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BookListResponse(BaseModel):
    items: List[BookResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
