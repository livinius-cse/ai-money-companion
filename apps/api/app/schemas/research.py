from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ResearchAssistanceRequest(BaseModel):
    focus_topic: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Specific subtopic or angle to research",
    )
    target_reader_question: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Specific reader question or problem to address",
    )

    model_config = ConfigDict(from_attributes=True)


class NicheAngle(BaseModel):
    angle_title: str
    core_premise: str
    differentiation_hook: str


class KeywordPhrase(BaseModel):
    phrase: str
    search_intent: str
    relevance_reason: str


class ResearchQuestionItem(BaseModel):
    category: str
    question: str
    strategic_objective: str


class ContentGapItem(BaseModel):
    missing_area: str
    reader_expectation: str
    suggested_chapter_or_section: str


class ResearchAssistanceResponse(BaseModel):
    book_id: str
    topic_refinement: List[NicheAngle]
    audience_positioning: Dict[str, Any]
    reader_profile_suggestions: Dict[str, Any]
    metadata_suggestions: Dict[str, Any]  # titles, subtitles, 7 keyword phrases, BISAC categories
    research_questions: List[ResearchQuestionItem]
    content_gap_analysis: List[ContentGapItem]
    publishing_preparation_checklist: List[str]
    facts: List[str] = Field(default_factory=list, description="Verified facts from current book concept and outline")
    assumptions: List[str] = Field(default_factory=list, description="Working assumptions regarding publishing audience")
    ai_suggestions: List[str] = Field(default_factory=list, description="AI strategic suggestions requiring author validation")
    missing_external_research: List[str] = Field(
        default_factory=list,
        description="External evidence that was not researched and must be independently verified",
    )

    model_config = ConfigDict(from_attributes=True)
