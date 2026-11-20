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


@pytest.mark.asyncio
async def test_coloring_book_prompt_uses_coloring_plan_despite_generic_page_budget():
    provider = MockAIProvider()
    prompt = (
        "Generate a structured publishing plan for a book with topic: "
        "'Children's coloring book featuring 50 cute animal designs with bold outlines', "
        "target audience: 'Children aged 4-8', book type: 'LOW_CONTENT', "
        "format: 'paperback', trim size: '8.5x11', paper: 'white_bw', "
        "target page budget: 106 pages."
    )

    result = await provider.generate_structured(prompt, BookPlanResponse)

    assert result.data.title_options[0] == "Limona: Cute Animals Coloring Book for Kids"
    assert result.data.chapters[0].title == "Woodland and Forest Friends"
    assert sum(chapter.allocated_pages for chapter in result.data.chapters) == 100
    assert result.data.front_matter_pages + sum(
        chapter.allocated_pages for chapter in result.data.chapters
    ) + result.data.back_matter_pages == 106


@pytest.mark.asyncio
async def test_generic_page_budget_does_not_select_finance_plan():
    provider = MockAIProvider()
    prompt = (
        "Generate a structured publishing plan for a book with topic: "
        "'A beginner-friendly guide to growing herbs at home', "
        "target audience: 'New gardeners', book type: 'NON_FICTION', "
        "format: 'paperback', trim size: '6x9', paper: 'white_bw', "
        "target page budget: 100 pages."
    )

    result = await provider.generate_structured(prompt, BookPlanResponse)

    assert result.data.title_options[0] == "The Practical Blueprint"
    assert "Money" not in result.data.title_options[0]
