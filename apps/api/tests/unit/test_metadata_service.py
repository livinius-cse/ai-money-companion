import pytest
from unittest.mock import patch
from app.services.metadata_generation import MetadataGenerationService
from app.schemas.metadata import MetadataGenerateRequest, KDPMetadataResponse
from app.ai.base import AIResponseEnvelope, AIExecutionMetadata


@pytest.mark.asyncio
async def test_metadata_generation_success():
    """Verify standard metadata generation with default mock provider."""
    request = MetadataGenerateRequest(
        title="Personal Finance Playbook",
        subtitle="The Complete Beginner Budgeting Guide",
        topic_summary="A comprehensive manual explaining debt snowball, indexing, and high yield savings.",
        target_audience="Young working adults aged 22-35",
    )

    metadata = await MetadataGenerationService.generate_metadata(request)

    # Verify keywords (1 to 7)
    assert 1 <= len(metadata.keywords) <= 7
    # Verify categories (1 to 3)
    assert 1 <= len(metadata.categories) <= 3
    # Verify description HTML is valid
    assert "<p>" in metadata.description_html
    assert "</p>" in metadata.description_html
    # Verify plain text summary
    assert len(metadata.plain_text_summary) > 0
    # Verify AI disclosure draft recommendation is strictly unconfirmed
    assert metadata.unconfirmed_disclosure_recommendation["author_confirmed"] is False


@pytest.mark.asyncio
async def test_metadata_keyword_length_advisories():
    """Verify advisory emitted when a keyword exceeds 50 characters."""
    request = MetadataGenerateRequest(
        title="Simple Budgeting",
        topic_summary="Budgeting guide",
        target_audience="General audience",
    )

    long_keyword = "a" * 55
    mock_metadata = KDPMetadataResponse(
        keywords=[long_keyword, "valid keyword"],
        categories=["NON_FICTION / Personal Finance"],
        description_html="<p>Valid description</p>",
        plain_text_summary="Plain text summary",
        unconfirmed_disclosure_recommendation={"author_confirmed": False},
        keyword_advisories=[],
    )

    mock_envelope = AIResponseEnvelope[KDPMetadataResponse](
        data=mock_metadata,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        result = await MetadataGenerationService.generate_metadata(request)
        assert any("exceeds 50 characters" in adv for adv in result.keyword_advisories)


@pytest.mark.asyncio
async def test_metadata_title_repetition_advisories():
    """Verify advisory emitted when keywords repeat words from book title."""
    request = MetadataGenerateRequest(
        title="Mastering Personal Budgeting",
        topic_summary="Budgeting guide",
        target_audience="General audience",
    )

    # Title words > 3 chars: "mastering", "personal", "budgeting"
    mock_metadata = KDPMetadataResponse(
        keywords=["mastering habits", "unrelated savings"],
        categories=["NON_FICTION / Personal Finance"],
        description_html="<p>Valid description</p>",
        plain_text_summary="Plain text summary",
        unconfirmed_disclosure_recommendation={"author_confirmed": False},
        keyword_advisories=[],
    )

    mock_envelope = AIResponseEnvelope[KDPMetadataResponse](
        data=mock_metadata,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        result = await MetadataGenerationService.generate_metadata(request)
        assert any("repeats title words" in adv for adv in result.keyword_advisories)


@pytest.mark.asyncio
async def test_metadata_prohibited_html_tags_rejection():
    """Verify ValueError is raised if AI output contains disallowed HTML tags."""
    request = MetadataGenerateRequest(
        title="Investing Basics",
        topic_summary="Investing guide",
        target_audience="General audience",
    )

    mock_metadata = KDPMetadataResponse(
        keywords=["investing basics"],
        categories=["NON_FICTION / Investing"],
        description_html="<p>Great guide <script>alert('xss')</script></p>",
        plain_text_summary="Plain text summary",
        unconfirmed_disclosure_recommendation={"author_confirmed": False},
    )

    mock_envelope = AIResponseEnvelope[KDPMetadataResponse](
        data=mock_metadata,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        with pytest.raises(ValueError) as exc_info:
            await MetadataGenerationService.generate_metadata(request)
        assert "Generated description violates KDP HTML rules" in str(exc_info.value)
        assert "script" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_metadata_prohibited_html_attributes_rejection():
    """Verify ValueError is raised if AI output contains HTML attributes."""
    request = MetadataGenerateRequest(
        title="Investing Basics",
        topic_summary="Investing guide",
        target_audience="General audience",
    )

    mock_metadata = KDPMetadataResponse(
        keywords=["investing basics"],
        categories=["NON_FICTION / Investing"],
        description_html='<p class="highlight">Text with forbidden attribute</p>',
        plain_text_summary="Plain text summary",
        unconfirmed_disclosure_recommendation={"author_confirmed": False},
    )

    mock_envelope = AIResponseEnvelope[KDPMetadataResponse](
        data=mock_metadata,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        with pytest.raises(ValueError) as exc_info:
            await MetadataGenerationService.generate_metadata(request)
        assert "Generated description violates KDP HTML rules" in str(exc_info.value)
        assert "attribute" in str(exc_info.value).lower()
