import asyncio
import time
import logging
from typing import Type, TypeVar, Optional
import httpx
from pydantic import BaseModel
from app.core.config import settings
from app.ai.base import BaseAIProvider, AIResponseEnvelope, AIExecutionMetadata
from app.ai.mock_provider import MockAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.exceptions import (
    AIError,
    AIProviderError,
    AITimeoutError,
    AIRateLimitError,
    AIConfigurationError,
)

logger = logging.getLogger("ai.factory")
T = TypeVar("T", bound=BaseModel)

SAFE_ERROR_MESSAGES = {
    "UPSTREAM_TIMEOUT": "The AI provider did not respond within the allocated timeout.",
    "UPSTREAM_RATE_LIMITED": "The AI provider quota has been temporarily exhausted.",
    "UPSTREAM_AUTH_FAILED": "The AI provider rejected backend credentials.",
    "UPSTREAM_SERVICE_UNAVAILABLE": "The upstream AI provider is currently unavailable.",
    "UPSTREAM_CONNECTION_REFUSED": "Unable to establish connection to upstream AI provider.",
    "INTERNAL_AI_ERROR": "An internal error occurred while processing the AI request.",
}


def map_exception_to_safe_code(e: Exception) -> str:
    """Map any exception to a controlled, safe internal error code."""
    if isinstance(e, AITimeoutError):
        return "UPSTREAM_TIMEOUT"
    if isinstance(e, AIRateLimitError):
        return "UPSTREAM_RATE_LIMITED"
    if isinstance(e, AIConfigurationError):
        return "UPSTREAM_AUTH_FAILED"
    if isinstance(e, httpx.TimeoutException):
        return "UPSTREAM_TIMEOUT"
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 429:
            return "UPSTREAM_RATE_LIMITED"
        if status in (401, 403):
            return "UPSTREAM_AUTH_FAILED"
        if status >= 500:
            return "UPSTREAM_SERVICE_UNAVAILABLE"
    if isinstance(e, httpx.RequestError):
        return "UPSTREAM_CONNECTION_REFUSED"
    return "INTERNAL_AI_ERROR"


class AIProviderFactory:
    """
    Factory creating and executing AI providers with strict fallback governance.
    Never silently substitutes mock responses when an external provider fails.
    """

    @staticmethod
    def get_provider(name: Optional[str] = None) -> BaseAIProvider:
        target = name or settings.AI_PROVIDER
        if target == "mock":
            return MockAIProvider()
        if target == "gemini":
            if not settings.GEMINI_API_KEY:
                raise AIConfigurationError("GEMINI_API_KEY not configured on backend.")
            return GeminiProvider(api_key=settings.GEMINI_API_KEY)
        raise AIConfigurationError(f"Unsupported AI provider: {target}")

    @staticmethod
    async def execute_structured(
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> AIResponseEnvelope[T]:
        requested_provider = settings.AI_PROVIDER
        primary = AIProviderFactory.get_provider(requested_provider)
        start_time = time.monotonic()
        timeout = timeout_seconds or settings.AI_TIMEOUT_SECONDS

        try:
            return await primary.generate_structured(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
                timeout_seconds=timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            safe_code = map_exception_to_safe_code(e)
            safe_msg = SAFE_ERROR_MESSAGES[safe_code]
            logger.error("Primary AI provider '%s' failed with code %s", requested_provider, safe_code)

            # Strict backend-only fallback governance (Client headers are ignored)
            if not settings.AI_ALLOW_FALLBACK:
                if isinstance(e, AITimeoutError):
                    raise AITimeoutError(safe_msg) from e
                if isinstance(e, AIRateLimitError):
                    raise AIRateLimitError(safe_msg) from e
                if isinstance(e, AIConfigurationError):
                    raise AIConfigurationError(safe_msg) from e
                raise AIProviderError(safe_msg) from e

            # Explicitly enabled fallback in backend configuration
            logger.warning("Executing configured fallback to MockAIProvider.")
            mock_provider = MockAIProvider()
            mock_res = await mock_provider.generate_structured(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
            )
            mock_res.telemetry = AIExecutionMetadata(
                requested_provider=requested_provider,  # type: ignore[arg-type]
                actual_provider="mock",
                is_mock_generated=True,
                model_name="mock-deterministic-v1",
                execution_duration_ms=duration_ms,
                is_fallback=True,
                fallback_reason=f"Primary provider '{requested_provider}' failed: {safe_msg}",
            )
            return mock_res
