import asyncio
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from app.ai.gemini_provider import GeminiProvider
from app.ai.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AITimeoutError,
    AIRateLimitError,
)
from app.schemas.planning import BookPlanResponse


def test_gemini_provider_empty_key():
    with pytest.raises(AIConfigurationError):
        GeminiProvider(api_key="")


@pytest.mark.asyncio
async def test_gemini_provider_cancellation_propagation():
    """Verify that asyncio.CancelledError is never swallowed or converted into AIProviderError."""
    provider = GeminiProvider(api_key="test_fake_api_key_for_unit_tests")

    with patch("httpx.AsyncClient.post", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await provider.generate_text("Prompt")


@pytest.mark.asyncio
async def test_gemini_provider_timeout_mapping():
    provider = GeminiProvider(api_key="test_fake_api_key_for_unit_tests")

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
        with pytest.raises(AITimeoutError) as exc_info:
            await provider.generate_text("Prompt", timeout_seconds=10.0)
        assert "timed out" in str(exc_info.value).lower()
        # Verify API key is NOT leaked in message
        assert "test_fake_api_key" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_mapping():
    provider = GeminiProvider(api_key="test_fake_api_key_for_unit_tests")

    mock_resp = httpx.Response(status_code=429, request=httpx.Request("POST", "https://example.com"))
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPStatusError("Rate limit", request=mock_resp.request, response=mock_resp)):
        with pytest.raises(AIRateLimitError) as exc_info:
            await provider.generate_text("Prompt")
        assert "rate limit" in str(exc_info.value).lower()
        assert "test_fake_api_key" not in str(exc_info.value)
