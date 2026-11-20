from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


class RecommendationItem(BaseModel):
    id: str
    title: str
    category: Literal[
        "SALES_PERFORMANCE",
        "MARKETPLACE_OPPORTUNITY",
        "REPORTING_GAP",
        "METADATA_OPTIMIZATION",
        "CATALOG_EXPANSION",
    ]
    supporting_evidence: str = Field(..., description="Factual basis derived strictly from actual imported data or book config")
    suggested_action: str = Field(..., description="Actionable publishing step for the author")
    provenance: Literal["REAL_KDP_REPORT", "SIMULATED_DEMO", "METADATA_SPEC"]
    disclaimer: str = "Historical observations only. Never guarantees future royalties or performance."

    model_config = ConfigDict(from_attributes=True)


class BusinessRecommendationResponse(BaseModel):
    book_id: str
    book_title: str
    total_recommendations: int
    recommendations: List[RecommendationItem]
    data_sources_evaluated: List[str]
    demo_disclaimer: Optional[str] = None
    disclaimer: str = "Evidence-based strategic guidance. Past performance does not guarantee future earnings on Amazon KDP."

    model_config = ConfigDict(from_attributes=True)
