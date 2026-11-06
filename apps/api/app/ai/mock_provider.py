import time
import hashlib
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.ai.base import BaseAIProvider, AIResponseEnvelope, AIExecutionMetadata
from app.ai.exceptions import AIProviderError, AITimeoutError, AIRateLimitError
from app.ai.mock_fixtures import DEFAULT_PLANNING_FIXTURES, DEFAULT_METADATA_FIXTURES
from app.schemas.planning import BookPlanResponse
from app.schemas.metadata import KDPMetadataResponse

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
        topic_key = "finance" if any(k in prompt_lower for k in ["money", "finance", "budget", "wealth", "invest", "debt"]) else "default"

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
