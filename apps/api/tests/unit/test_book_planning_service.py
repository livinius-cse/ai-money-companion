import pytest
from unittest.mock import patch
from app.services.book_planning import BookPlanningService
from app.schemas.planning import BookPlanRequest, BookPlanResponse, ChapterPlanItem
from app.ai.base import AIResponseEnvelope, AIExecutionMetadata


@pytest.mark.asyncio
async def test_book_planning_pure_page_calculation():
    """Verify pure page math calculation, even page handling, and specification matching."""
    request = BookPlanRequest(
        topic="Personal Finance Fundamentals",
        target_audience="Beginners aged 20-35",
        book_type="NON_FICTION",
        print_format="paperback",
        target_trim_size="6x9",
        paper_type="white_bw",
        target_pages=100,
    )

    plan = await BookPlanningService.plan_book(request)

    # 4 front + (14 + 16 + 18 + 14 + 18 + 14) + 2 back = 100 pages
    assert plan.total_calculated_pages == 100
    assert plan.is_odd_page_count is False
    assert plan.kdp_manufacturing_notice is None
    assert plan.specification_matched is True
    assert plan.spec_id == "PB-US-6X9-BW"


@pytest.mark.asyncio
async def test_book_planning_odd_page_notice():
    """Verify odd page count sets flag and manufacturing parity notice without barcode claims."""
    request = BookPlanRequest(
        topic="Investing Basics",
        target_audience="Young Adults",
        target_trim_size="6x9",
        paper_type="white_bw",
    )

    mock_plan = BookPlanResponse(
        title_options=["Title 1"],
        subtitle_options=["Subtitle 1"],
        target_reader_avatar="Young Adult",
        front_matter_pages=5,  # 5 + 94 + 2 = 101 pages (odd)
        chapters=[
            ChapterPlanItem(
                chapter_number=i,
                title=f"Chapter {i}",
                summary="Chapter summary here",
                key_takeaways=["Takeaway"],
                estimated_word_count=2000,
                allocated_pages=10,
            )
            for i in range(1, 10)  # 9 chapters * 10 = 90 pages
        ],
        back_matter_pages=2,
        total_calculated_pages=0,
        is_odd_page_count=False,
    )
    # Total = 5 + 90 + 2 = 97 pages (odd)

    mock_envelope = AIResponseEnvelope[BookPlanResponse](
        data=mock_plan,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock-deterministic-v1",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        plan = await BookPlanningService.plan_book(request)

        assert plan.total_calculated_pages == 97
        assert plan.is_odd_page_count is True
        assert plan.kdp_manufacturing_notice == (
            "KDP rounds an odd interior page count up to the nearest even number of whole sheets."
        )
        assert "barcode" not in plan.kdp_manufacturing_notice.lower()


@pytest.mark.asyncio
async def test_book_planning_minimum_page_limit_rejection():
    """Verify rejection when total pages is below minimum paperback limit (24 pages)."""
    request = BookPlanRequest(
        topic="Brief Summary Guide",
        target_audience="General",
        target_trim_size="6x9",
        paper_type="white_bw",
    )

    mock_plan = BookPlanResponse(
        title_options=["Title"],
        subtitle_options=["Subtitle"],
        target_reader_avatar="General",
        front_matter_pages=2,
        chapters=[
            ChapterPlanItem(
                chapter_number=1,
                title="Single Short Chapter",
                summary="Summary text here",
                estimated_word_count=1500,
                allocated_pages=10,
            )
        ],
        back_matter_pages=2,
        total_calculated_pages=0,
        is_odd_page_count=False,
    )
    # Total = 2 + 10 + 2 = 14 pages (< 24)

    mock_envelope = AIResponseEnvelope[BookPlanResponse](
        data=mock_plan,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock-deterministic-v1",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        with pytest.raises(ValueError) as exc_info:
            await BookPlanningService.plan_book(request)

        assert "KDP specification limits" in str(exc_info.value)
        assert "minimum 24" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_book_planning_cream_paper_maximum_rejection():
    """Verify rejection when total pages exceeds 6x9 cream paper maximum (776 pages)."""
    request = BookPlanRequest(
        topic="Comprehensive Financial Encyclopedia",
        target_audience="Finance Students",
        target_trim_size="6x9",
        paper_type="cream_bw",
    )

    mock_plan = BookPlanResponse(
        title_options=["Title"],
        subtitle_options=["Subtitle"],
        target_reader_avatar="Students",
        front_matter_pages=4,
        chapters=[
            ChapterPlanItem(
                chapter_number=1,
                title="Enormous Chapter",
                summary="Summary text here",
                estimated_word_count=20000,
                allocated_pages=155,
            )
            for _ in range(5)  # 5 * 155 = 775
        ],
        back_matter_pages=2,
        total_calculated_pages=0,
        is_odd_page_count=False,
    )
    # Total = 4 + 775 + 2 = 781 pages (> 776)

    mock_envelope = AIResponseEnvelope[BookPlanResponse](
        data=mock_plan,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock-deterministic-v1",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        with pytest.raises(ValueError) as exc_info:
            await BookPlanningService.plan_book(request)

        assert "KDP specification limits" in str(exc_info.value)
        assert "776" in str(exc_info.value)


@pytest.mark.asyncio
async def test_book_planning_white_paper_maximum_rejection():
    """Verify rejection when total pages exceeds 6x9 white paper maximum (828 pages)."""
    request = BookPlanRequest(
        topic="Massive Reference Manual",
        target_audience="Professionals",
        target_trim_size="6x9",
        paper_type="white_bw",
    )

    mock_plan = BookPlanResponse(
        title_options=["Title"],
        subtitle_options=["Subtitle"],
        target_reader_avatar="Professionals",
        front_matter_pages=4,
        chapters=[
            ChapterPlanItem(
                chapter_number=1,
                title="Chapter",
                summary="Summary text here",
                estimated_word_count=20000,
                allocated_pages=165,
            )
            for _ in range(5)  # 5 * 165 = 825
        ],
        back_matter_pages=2,
        total_calculated_pages=0,
        is_odd_page_count=False,
    )
    # Total = 4 + 825 + 2 = 831 pages (> 828)

    mock_envelope = AIResponseEnvelope[BookPlanResponse](
        data=mock_plan,
        telemetry=AIExecutionMetadata(
            requested_provider="mock",
            actual_provider="mock",
            is_mock_generated=True,
            model_name="mock-deterministic-v1",
            execution_duration_ms=5,
        ),
    )

    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_envelope):
        with pytest.raises(ValueError) as exc_info:
            await BookPlanningService.plan_book(request)

        assert "KDP specification limits" in str(exc_info.value)
        assert "828" in str(exc_info.value)


@pytest.mark.asyncio
async def test_book_planning_hardcover_validation():
    """Verify hardcover trim, page limits (75-550), and unsupported options."""
    # 1. Valid hardcover (6x9, 100 pages, white_bw)
    valid_hc_req = BookPlanRequest(
        topic="Hardcover Edition",
        target_audience="Collectors",
        print_format="hardcover",
        target_trim_size="6x9",
        paper_type="white_bw",
    )
    plan = await BookPlanningService.plan_book(valid_hc_req)
    assert plan.total_calculated_pages == 100
    assert plan.specification_matched is True
    assert plan.spec_id == "HC-TECH-BW-6X9"

    # 2. Hardcover page count below 75 pages
    short_hc_plan = BookPlanResponse(
        title_options=["Title"],
        subtitle_options=["Subtitle"],
        target_reader_avatar="General",
        front_matter_pages=4,
        chapters=[
            ChapterPlanItem(
                chapter_number=1,
                title="Single Chapter",
                summary="Summary of this single chapter",
                estimated_word_count=5000,
                allocated_pages=50,
            )
        ],
        back_matter_pages=2,
        total_calculated_pages=0,
        is_odd_page_count=False,
    )
    # Total = 4 + 50 + 2 = 56 (< 75)
    mock_short_envelope = AIResponseEnvelope[BookPlanResponse](
        data=short_hc_plan,
        telemetry=AIExecutionMetadata(
            requested_provider="mock", actual_provider="mock", is_mock_generated=True,
            model_name="mock", execution_duration_ms=5,
        ),
    )
    with patch("app.ai.factory.AIProviderFactory.execute_structured", return_value=mock_short_envelope):
        with pytest.raises(ValueError) as exc_info:
            await BookPlanningService.plan_book(valid_hc_req)
        assert "minimum of 75" in str(exc_info.value).lower()

    # 3. Hardcover with prohibited standard_color
    color_hc_req = BookPlanRequest(
        topic="Hardcover Color",
        target_audience="General",
        print_format="hardcover",
        target_trim_size="6x9",
        paper_type="standard_color",
    )
    with pytest.raises(ValueError) as exc_info:
        await BookPlanningService.plan_book(color_hc_req)
    assert "prohibited for hardcover" in str(exc_info.value).lower()
