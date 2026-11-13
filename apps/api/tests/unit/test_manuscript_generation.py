import pytest
from app.ai.mock_provider import MockAIProvider
from app.services.manuscript_generation import ManuscriptGenerationService
from app.schemas.manuscript import (
    ManuscriptDraftRequest,
    SectionExpandRequest,
    SectionRegenerateRequest,
)


@pytest.mark.asyncio
async def test_draft_chapter_with_mock_provider():
    provider = MockAIProvider()
    service = ManuscriptGenerationService(provider=provider)

    req = ManuscriptDraftRequest(
        target_words=1500,
        tone="authoritative_practical",
        special_instructions="Emphasize zero-judgment reality check audit.",
    )

    envelope = await service.draft_chapter(
        book_title="The 30-Day Money Reset",
        book_topic="Personal Finance and Budgeting",
        target_audience="Working Professionals",
        chapter_number=1,
        chapter_title="Taking Stock: The Reality Check Audit",
        chapter_summary="Assess current net worth and identify spending leaks.",
        req=req,
    )

    data = envelope.data
    telemetry = envelope.telemetry

    assert data.chapter_title == "Taking Stock: The Reality Check Audit"
    assert len(data.markdown_content) > 100
    assert data.word_count > 50
    assert data.estimated_reading_minutes >= 1
    assert data.is_draft is True
    assert data.author_reviewed is False
    assert telemetry.is_mock_generated is True
    assert telemetry.actual_provider == "mock"


@pytest.mark.asyncio
async def test_expand_section_with_mock_provider():
    provider = MockAIProvider()
    service = ManuscriptGenerationService(provider=provider)

    req = SectionExpandRequest(
        section_heading="The 48-Hour Implementation Protocol",
        current_text="Cancel three subscriptions and consolidate high-interest balances.",
        expansion_guidance="Add step-by-step checklists.",
    )

    envelope = await service.expand_section(
        book_topic="Personal Finance",
        chapter_title="Taking Stock",
        req=req,
    )

    data = envelope.data
    assert len(data.expanded_markdown) > 50
    assert data.word_count > 10


@pytest.mark.asyncio
async def test_regenerate_section_with_mock_provider():
    provider = MockAIProvider()
    service = ManuscriptGenerationService(provider=provider)

    req = SectionRegenerateRequest(
        section_heading="Establishing Your True Net Worth Baseline",
        current_text="Net worth is not an ego metric.",
        alternative_instructions="Make it more concise and punchy.",
    )

    envelope = await service.regenerate_section(
        book_topic="Personal Finance",
        chapter_title="Taking Stock",
        req=req,
    )

    data = envelope.data
    assert len(data.regenerated_markdown) > 30
    assert data.word_count > 5
