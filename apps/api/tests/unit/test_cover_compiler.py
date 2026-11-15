import io
import pytest
import pypdf
from app.models.book import Book
from app.schemas.book_document import CoverGenerationRequest
from app.services.cover_calculation import CoverCalculationService
from app.services.cover_compiler import FullJacketCoverCompiler


def test_compile_paperback_cover_single_page_and_dimensions():
    book = Book(
        id="book-cov-1",
        owner_id="user-1",
        title="The Wealth Acceleration Matrix",
        subtitle="Tactical Strategies",
        topic="Finance",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
        target_page_count=100,
    )

    calc = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=100,
    )

    req = CoverGenerationRequest(
        custom_front_title="The Wealth Acceleration Matrix",
        custom_front_subtitle="Tactical Strategies",
        custom_author_name="Jane Doe",
        back_cover_description="A revolutionary framework for personal asset governance.",
        primary_color="#0f172a",
        accent_color="#f59e0b",
        include_spine_text=True,
        render_guides=False,
    )

    pdf_bytes, meta = FullJacketCoverCompiler.compile_cover(
        book=book,
        calc=calc,
        req=req,
    )

    assert len(pdf_bytes) > 1000
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

    # EXACTLY ONE PAGE
    assert len(reader.pages) == 1
    p1 = reader.pages[0]

    # Verify MediaBox matches calculated full cover dimensions
    assert abs(float(p1.mediabox.width) - calc.full_cover_width_pt) < 0.5
    assert abs(float(p1.mediabox.height) - calc.full_cover_height_pt) < 0.5


def test_compile_cover_below_spine_threshold():
    book = Book(
        id="book-cov-2",
        owner_id="user-1",
        title="Short Guide",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
    )
    # 40 pages -> spine text must be disabled
    calc = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=40,
    )
    assert calc.spine_text_eligible is False

    req = CoverGenerationRequest(
        custom_front_title="Short Guide",
        include_spine_text=True,  # Requested, but must be safely skipped due to < 80 pages
    )
    pdf_bytes, meta = FullJacketCoverCompiler.compile_cover(
        book=book,
        calc=calc,
        req=req,
    )

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1
    assert meta["spine_text_eligible"] is False
