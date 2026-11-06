import pytest
from app.ai.mock_provider import MockAIProvider
from app.ai.exceptions import AITimeoutError, AIRateLimitError, AIProviderError
from app.schemas.planning import BookPlanResponse
from app.schemas.metadata import KDPMetadataResponse


@pytest.mark.asyncio
async def test_mock_provider_determinism():
    provider = MockAIProvider()
    prompt = "Generate a book plan on personal finance and money budgeting."

    res1 = await provider.generate_structured(prompt, BookPlanResponse)
    res2 = await provider.generate_structured(prompt, BookPlanResponse)

    assert res1.data.title_options == res2.data.title_options
    assert res1.data.total_calculated_pages == res2.data.total_calculated_pages
    assert res1.telemetry.actual_provider == "mock"
    assert res1.telemetry.is_mock_generated is True
    assert res1.telemetry.is_fallback is False


@pytest.mark.asyncio
async def test_mock_provider_metadata_generation():
    provider = MockAIProvider()
    prompt = "Generate KDP keywords and HTML description for money guide."

    res = await provider.generate_structured(prompt, KDPMetadataResponse)
    assert len(res.data.keywords) == 7
    assert "<h4>" in res.data.description_html
    assert res.data.unconfirmed_disclosure_recommendation["author_confirmed"] is False


@pytest.mark.asyncio
async def test_mock_provider_fault_simulation():
    provider_timeout = MockAIProvider(simulate_failure="timeout")
    with pytest.raises(AITimeoutError):
        await provider_timeout.generate_text("test")

    provider_rate = MockAIProvider(simulate_failure="rate_limit")
    with pytest.raises(AIRateLimitError):
        await provider_rate.generate_text("test")

    provider_err = MockAIProvider(simulate_failure="error")
    with pytest.raises(AIProviderError):
        await provider_err.generate_text("test")
