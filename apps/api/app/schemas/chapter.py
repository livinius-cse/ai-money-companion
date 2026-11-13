from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class ChapterCreate(BaseModel):
    chapter_number: int = Field(default=1, ge=1, description="Sequential chapter order number")
    chapter_type: Literal["front_matter", "chapter", "back_matter"] = "chapter"
    title: str = Field(..., min_length=1, max_length=255, description="Chapter title")
    summary: Optional[str] = Field(default=None, description="Chapter synopsis/summary")
    content: Optional[str] = Field(default="", description="Markdown manuscript content")
    allocated_pages: int = Field(default=10, ge=1, le=100, description="Target page budget")
    draft_status: Literal["NOT_STARTED", "DRAFT", "IN_PROGRESS", "COMPLETED"] = "NOT_STARTED"

    model_config = ConfigDict(from_attributes=True)


class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    summary: Optional[str] = None
    content: Optional[str] = None
    allocated_pages: Optional[int] = Field(default=None, ge=1, le=100)
    chapter_type: Optional[Literal["front_matter", "chapter", "back_matter"]] = None
    draft_status: Optional[Literal["NOT_STARTED", "DRAFT", "IN_PROGRESS", "COMPLETED"]] = None

    model_config = ConfigDict(from_attributes=True)


class ChapterResponse(BaseModel):
    id: str
    book_id: str
    owner_id: str
    chapter_number: int
    chapter_type: str
    title: str
    summary: Optional[str] = None
    content: str
    allocated_pages: int
    word_count: int
    estimated_reading_minutes: int
    draft_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChapterReorderItem(BaseModel):
    chapter_id: str
    chapter_number: int = Field(..., ge=1)


class ChapterReorderRequest(BaseModel):
    reordered_chapters: List[ChapterReorderItem]
