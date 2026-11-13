import pytest
from app.ai.mock_provider import MockAIProvider
from app.services.illustration_prompt import IllustrationPromptService
from app.schemas.illustration import IllustrationPromptGenerateRequest
from app.core.storage import (
    detect_image_type,
    calculate_sha256,
    LocalAssetStorage,
    MAX_UPLOAD_SIZE_BYTES,
)


@pytest.mark.asyncio
async def test_illustration_prompt_generation_with_mock():
    provider = MockAIProvider()
    service = IllustrationPromptService(provider=provider)

    req = IllustrationPromptGenerateRequest(
        target_count=3,
        style_preset="modern_clean_vector",
        visual_instructions="Focus on debt payoff and cash flow charts.",
    )

    envelope = await service.generate_prompts(
        book_title="The 30-Day Money Reset",
        book_topic="Personal Finance",
        chapter_title="The Debt Elimination Engine",
        chapter_summary="Snowball vs avalanche payoff methods.",
        req=req,
    )

    data = envelope.data
    assert len(data.prompts) == 3
    assert all(p.prompt for p in data.prompts)
    assert all(p.style_preset for p in data.prompts)


def test_illustration_status_transitions():
    # 1. PROMPT -> PLACEHOLDER is valid without asset
    ok, err = IllustrationPromptService.validate_status_transition("PROMPT", "PLACEHOLDER", has_asset=False, human_approved=False)
    assert ok is True
    assert err is None

    # 2. PROMPT -> GENERATED fails without asset
    ok, err = IllustrationPromptService.validate_status_transition("PROMPT", "GENERATED", has_asset=False, human_approved=False)
    assert ok is False
    assert "without an uploaded image asset" in err

    # 3. PROMPT -> GENERATED succeeds with asset
    ok, err = IllustrationPromptService.validate_status_transition("PROMPT", "GENERATED", has_asset=True, human_approved=False)
    assert ok is True

    # 4. GENERATED -> APPROVED_FINAL fails without human_approved
    ok, err = IllustrationPromptService.validate_status_transition("GENERATED", "APPROVED_FINAL", has_asset=True, human_approved=False)
    assert ok is False
    assert "human approval" in err

    # 5. GENERATED -> APPROVED_FINAL succeeds with human_approved and asset
    ok, err = IllustrationPromptService.validate_status_transition("GENERATED", "APPROVED_FINAL", has_asset=True, human_approved=True)
    assert ok is True

    # 6. Invalid transition: PROMPT directly to APPROVED_FINAL
    ok, err = IllustrationPromptService.validate_status_transition("PROMPT", "APPROVED_FINAL", has_asset=True, human_approved=True)
    assert ok is False
    assert "Invalid status transition" in err


def test_image_signature_validation():
    # Valid PNG header (89 50 4E 47 0D 0A 1A 0A)
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    detected = detect_image_type(png_bytes)
    assert detected is not None
    assert detected[0] == "image/png"
    assert detected[1] == ".png"

    # Valid JPEG header (FF D8 FF)
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    detected_jpeg = detect_image_type(jpeg_bytes)
    assert detected_jpeg is not None
    assert detected_jpeg[0] == "image/jpeg"

    # Valid WebP header (RIFF .... WEBP)
    webp_bytes = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 20
    detected_webp = detect_image_type(webp_bytes)
    assert detected_webp is not None
    assert detected_webp[0] == "image/webp"

    # Fake image (e.g. plain text or exe)
    fake_bytes = b"Hello world, I am a text file pretending to be an image!"
    assert detect_image_type(fake_bytes) is None


def test_sha256_calculation():
    sample = b"AI Money Companion Illustration Asset Data"
    h = calculate_sha256(sample)
    assert len(h) == 64
    assert h == calculate_sha256(sample)
