from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class IllustrationCreate(BaseModel):
    chapter_id: Optional[str] = None
    prompt: str = Field(..., min_length=1, description="Detailed generation or creative prompt")
    description: Optional[str] = None
    style_preset: Optional[str] = "modern_clean_vector"
    seed: Optional[str] = None
    position_description: Optional[str] = None
    status: Literal["PROMPT", "PLACEHOLDER"] = "PROMPT"

    model_config = ConfigDict(from_attributes=True)


class IllustrationUpdate(BaseModel):
    chapter_id: Optional[str] = None
    prompt: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
    style_preset: Optional[str] = None
    seed: Optional[str] = None
    position_description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IllustrationStatusUpdate(BaseModel):
    status: Literal["PROMPT", "PLACEHOLDER", "GENERATED", "APPROVED_FINAL"]
    human_approved: bool = Field(default=False, description="Explicit approval confirmation by the publisher")
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class IllustrationResponse(BaseModel):
    id: str
    book_id: str
    chapter_id: Optional[str] = None
    owner_id: str
    prompt: str
    description: Optional[str] = None
    style_preset: Optional[str] = None
    seed: Optional[str] = None
    position_description: Optional[str] = None
    status: str
    storage_key: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    sha256_hash: Optional[str] = None
    asset_source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IllustrationPromptGenerateRequest(BaseModel):
    chapter_id: Optional[str] = None
    target_count: int = Field(default=3, ge=1, le=10)
    style_preset: Optional[str] = "clean_minimalist_line_art"
    visual_instructions: Optional[str] = None


class IllustrationPromptItem(BaseModel):
    prompt: str
    description: str
    style_preset: str
    suggested_placement: str


class IllustrationPromptGenerateResponse(BaseModel):
    prompts: List[IllustrationPromptItem]
