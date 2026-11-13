from typing import Optional
from pydantic import BaseModel, Field


class ManuscriptDraftRequest(BaseModel):
    target_words: int = Field(default=1500, ge=100, le=10000, description="Desired word count budget")
    tone: Optional[str] = Field(default="authoritative_practical", description="Narrative tone")
    special_instructions: Optional[str] = Field(default=None, description="Guidance or focus areas")


class ManuscriptDraftResponse(BaseModel):
    chapter_title: str
    markdown_content: str
    word_count: int
    estimated_reading_minutes: int
    is_draft: bool = True
    author_reviewed: bool = False


class SectionExpandRequest(BaseModel):
    section_heading: str = Field(..., min_length=1)
    current_text: str = Field(..., min_length=1)
    expansion_guidance: Optional[str] = None


class SectionExpandResponse(BaseModel):
    section_heading: str
    expanded_markdown: str
    word_count: int


class SectionRegenerateRequest(BaseModel):
    section_heading: str = Field(..., min_length=1)
    current_text: str = Field(..., min_length=1)
    alternative_instructions: Optional[str] = None


class SectionRegenerateResponse(BaseModel):
    section_heading: str
    regenerated_markdown: str
    word_count: int
