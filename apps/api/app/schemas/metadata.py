from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MetadataGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    topic_summary: str = Field(..., min_length=10, max_length=2000)
    target_audience: str = Field(..., min_length=3, max_length=200)


class KDPMetadataResponse(BaseModel):
    keywords: List[str] = Field(
        ...,
        min_length=1,
        max_length=7,
        description="Between 1 and 7 high-intent KDP search keyword phrases."
    )
    keyword_advisories: List[str] = Field(default_factory=list)
    categories: List[str] = Field(..., min_length=1, max_length=3)
    description_html: str = Field(..., max_length=4000)
    plain_text_summary: str = Field(..., max_length=1000)
    unconfirmed_disclosure_recommendation: Dict[str, Any] = Field(default_factory=dict)
