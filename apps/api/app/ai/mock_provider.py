import time
import hashlib
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.ai.base import BaseAIProvider, AIResponseEnvelope, AIExecutionMetadata
from app.ai.exceptions import AIProviderError, AITimeoutError, AIRateLimitError
from app.ai.mock_fixtures import (
    DEFAULT_PLANNING_FIXTURES,
    DEFAULT_METADATA_FIXTURES,
    DEFAULT_MANUSCRIPT_FIXTURES,
    DEFAULT_ILLUSTRATION_PROMPT_FIXTURES,
)
from app.schemas.planning import BookPlanResponse
from app.schemas.metadata import KDPMetadataResponse
from app.schemas.manuscript import (
    ManuscriptDraftResponse,
    SectionExpandResponse,
    SectionRegenerateResponse,
)
from app.schemas.illustration import (
    IllustrationPromptGenerateResponse,
    IllustrationPromptItem,
)
from app.schemas.research import (
    ResearchAssistanceResponse,
    NicheAngle,
    ResearchQuestionItem,
    ContentGapItem,
)

T = TypeVar("T", bound=BaseModel)


class MockAIProvider(BaseAIProvider):
    """
    100% offline, zero-cost, deterministic AI provider.
    Generates consistent, schema-valid output based on prompt hashing.
    """

    def __init__(self, simulate_failure: Optional[str] = None):
        self.simulate_failure = simulate_failure

    def get_provider_name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def _check_simulated_failure(self):
        if self.simulate_failure == "timeout":
            raise AITimeoutError("Mock provider simulated timeout after 30.0s")
        if self.simulate_failure == "rate_limit":
            raise AIRateLimitError("Mock provider simulated rate limit rejection")
        if self.simulate_failure == "error":
            raise AIProviderError("Mock provider simulated upstream failure")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout_seconds: Optional[float] = None,
    ) -> AIResponseEnvelope[str]:
        start = time.monotonic()
        self._check_simulated_failure()

        # Deterministic text generation based on prompt hash
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        generated_text = (
            f"[MockAI Response {h}]: Structured generation completed offline. "
            f"Prompt length: {len(prompt)} chars."
        )

        duration = int((time.monotonic() - start) * 1000)
        return AIResponseEnvelope[str](
            data=generated_text,
            telemetry=AIExecutionMetadata(
                requested_provider="mock",
                actual_provider="mock",
                is_mock_generated=True,
                model_name="mock-deterministic-v1",
                execution_duration_ms=duration,
                is_fallback=False,
            ),
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> AIResponseEnvelope[T]:
        start = time.monotonic()
        self._check_simulated_failure()

        prompt_lower = prompt.lower()

        # Classify specific product formats before broad subject categories.
        # Avoid the generic phrase "target page budget" accidentally selecting
        # the finance fixture for every book.
        coloring_terms = (
            "coloring book",
            "colouring book",
            "coloring pages",
            "colouring pages",
        )
        finance_terms = (
            "personal finance",
            "financial planning",
            "money management",
            "budgeting",
            "debt repayment",
            "debt payoff",
            "investing",
            "wealth building",
            "cash flow",
            "credit card debt",
        )
        if any(term in prompt_lower for term in coloring_terms):
            topic_key = "coloring"
        elif any(term in prompt_lower for term in finance_terms):
            topic_key = "finance"
        else:
            topic_key = "default"

        data: Any
        if issubclass(response_model, BookPlanResponse):
            fix = DEFAULT_PLANNING_FIXTURES[topic_key]
            total_pages = fix["front_matter_pages"] + sum(c["allocated_pages"] for c in fix["chapters"]) + fix["back_matter_pages"]
            is_odd = total_pages % 2 != 0
            notice = None
            if is_odd:
                notice = "KDP rounds an odd interior page count up to the nearest even number of whole sheets."

            data = BookPlanResponse(
                title_options=fix["title_options"],
                subtitle_options=fix["subtitle_options"],
                target_reader_avatar=fix["target_reader_avatar"],
                front_matter_pages=fix["front_matter_pages"],
                chapters=fix["chapters"],
                back_matter_pages=fix["back_matter_pages"],
                total_calculated_pages=total_pages,
                is_odd_page_count=is_odd,
                kdp_manufacturing_notice=notice,
                specification_matched=True,
                spec_id="PB-US-6X9-BW",
                specification_advisory=None,
            )
        elif issubclass(response_model, KDPMetadataResponse):
            fix = DEFAULT_METADATA_FIXTURES[topic_key]
            data = KDPMetadataResponse(
                keywords=fix["keywords"],
                keyword_advisories=fix["keyword_advisories"],
                categories=fix["categories"],
                description_html=fix["description_html"],
                plain_text_summary=fix["plain_text_summary"],
                unconfirmed_disclosure_recommendation=fix["unconfirmed_disclosure_recommendation"],
            )
        elif issubclass(response_model, ManuscriptDraftResponse):
            fix = DEFAULT_MANUSCRIPT_FIXTURES.get(topic_key, DEFAULT_MANUSCRIPT_FIXTURES["default"])
            content = fix["markdown_content"]
            words = len(content.split())
            reading_mins = max(1, round(words / 200))
            data = ManuscriptDraftResponse(
                chapter_title=fix["chapter_title"],
                markdown_content=content,
                word_count=words,
                estimated_reading_minutes=reading_mins,
                is_draft=True,
                author_reviewed=False,
            )
        elif issubclass(response_model, SectionExpandResponse):
            expanded_text = (
                f"### Detailed Operational Deep-Dive\n\n"
                f"Expanding upon the foundational concepts with practical implementation protocols. "
                f"Key factors to consider include cadence, automated checks, and systematic friction reduction. "
                f"By institutionalizing these steps into a 7-day checklist, progress remains steady and measurable.\n\n"
                f"1. **Pre-execution verification:** Confirm dependencies and baselines.\n"
                f"2. **Continuous alignment:** Run weekly audits against planned targets.\n"
                f"3. **Milestone celebration:** Reinforce behavioral adherence."
            )
            data = SectionExpandResponse(
                section_heading="Expanded Section",
                expanded_markdown=expanded_text,
                word_count=len(expanded_text.split()),
            )
        elif issubclass(response_model, SectionRegenerateResponse):
            regen_text = (
                f"### Strategic Restructuring\n\n"
                f"A refined analytical approach to this section emphasizing practical efficiency and cognitive clarity. "
                f"Rather than reactive problem solving, establish proactive environmental safeguards that eliminate friction at the source."
            )
            data = SectionRegenerateResponse(
                section_heading="Regenerated Section",
                regenerated_markdown=regen_text,
                word_count=len(regen_text.split()),
            )
        elif issubclass(response_model, IllustrationPromptGenerateResponse):
            fix_prompts = DEFAULT_ILLUSTRATION_PROMPT_FIXTURES.get(topic_key, DEFAULT_ILLUSTRATION_PROMPT_FIXTURES["default"])
            items = [IllustrationPromptItem(**p) for p in fix_prompts]
            data = IllustrationPromptGenerateResponse(prompts=items)
        elif issubclass(response_model, ResearchAssistanceResponse):
            data = ResearchAssistanceResponse(
                book_id="",
                topic_refinement=[
                    NicheAngle(
                        angle_title="Practical foundations",
                        core_premise="Explain the persisted topic through clear foundational concepts.",
                        differentiation_hook="Use the book's actual outline and reader questions to set scope.",
                    )
                ],
                audience_positioning={
                    "positioning": "A practical guide shaped by the audience already specified for this book.",
                    "evidence_status": "AI suggestion; validate with readers.",
                },
                reader_profile_suggestions={
                    "profile": "Use the persisted target audience as the starting point.",
                    "evidence_status": "Assumption; not based on external reader research.",
                },
                metadata_suggestions={
                    "title_ideas": [],
                    "subtitle_ideas": [],
                    "keyword_phrases": [],
                    "category_ideas": [],
                    "note": "Suggestions only; no search volume or ranking data was used.",
                },
                research_questions=[
                    ResearchQuestionItem(
                        category="Reader needs",
                        question="What practical question should a reader be able to answer after this section?",
                        strategic_objective="Use the answer to validate chapter scope.",
                    )
                ],
                content_gap_analysis=[
                    ContentGapItem(
                        missing_area="Evidence and examples",
                        reader_expectation="Readers may expect claims to be supported with traceable sources.",
                        suggested_chapter_or_section="Identify claims that need primary-source verification.",
                    )
                ],
                publishing_preparation_checklist=[
                    "Verify factual claims against primary sources.",
                    "Review all metadata suggestions before use.",
                ],
                assumptions=[],
                ai_suggestions=[
                    "Review the proposed scope and examples with the intended readers."
                ],
                missing_external_research=[
                    "No external demand, keyword-volume, ranking, competitor, review, or market research was performed."
                ],
            )
        else:
            # Fallback for generic models
            data = response_model.model_validate({})

        duration = int((time.monotonic() - start) * 1000)
        return AIResponseEnvelope[T](
            data=data,
            telemetry=AIExecutionMetadata(
                requested_provider="mock",
                actual_provider="mock",
                is_mock_generated=True,
                model_name="mock-deterministic-v1",
                execution_duration_ms=duration,
                is_fallback=False,
            ),
        )
