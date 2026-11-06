import pytest
from unittest.mock import patch
from app.core.config import settings
from app.ai.factory import AIProviderFactory, map_exception_to_safe_code, SAFE_ERROR_MESSAGES
from app.ai.exceptions import AIProviderError, AITimeoutError
from app.schemas.planning import BookPlanResponse


def test_map_exception_to_safe_code():
    assert map_exception_to_safe_code(AITimeoutError("timeout")) == "UPSTREAM_TIMEOUT"
    assert "timeout" in SAFE_ERROR_MESSAGES["UPSTREAM_TIMEOUT"].lower()


@pytest.mark.asyncio
async def test_fallback_disabled_by_default():
    """Verify that when AI_ALLOW_FALLBACK is False, Gemini failure raises AIProviderError and NEVER returns mock."""
    with patch.object(settings, "AI_PROVIDER", "gemini"), \
         patch.object(settings, "GEMINI_API_KEY", "fake_gemini_key_12345"), \
         patch.object(settings, "AI_ALLOW_FALLBACK", False), \
         patch("app.ai.gemini_provider.GeminiProvider.generate_structured", side_effect=AIProviderError("Internal upstream fault")):

        with pytest.raises(AIProviderError) as exc_info:
            await AIProviderFactory.execute_structured("Prompt", BookPlanResponse)

        # Message is sanitized
        assert "Internal upstream fault" not in str(exc_info.value)
        assert "fake_gemini_key" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_fallback_enabled_via_backend_config():
    """Verify that when AI_ALLOW_FALLBACK is True, Gemini failure executes mock with explicit telemetry."""
    with patch.object(settings, "AI_PROVIDER", "gemini"), \
         patch.object(settings, "GEMINI_API_KEY", "fake_gemini_key_12345"), \
         patch.object(settings, "AI_ALLOW_FALLBACK", True), \
         patch("app.ai.gemini_provider.GeminiProvider.generate_structured", side_effect=AIProviderError("Internal fault")):

        result = await AIProviderFactory.execute_structured("Prompt for personal finance", BookPlanResponse)

        assert result.telemetry.is_fallback is True
        assert result.telemetry.actual_provider == "mock"
        assert result.telemetry.requested_provider == "gemini"
        assert result.telemetry.is_mock_generated is True
        assert "Primary provider 'gemini' failed" in result.telemetry.fallback_reason
        assert "fake_gemini_key" not in result.telemetry.fallback_reason
