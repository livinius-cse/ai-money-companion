import io
import pytest
import pypdf
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.schemas.book_document import InteriorGenerationRequest
from app.services.interior_compiler import InteriorPDFCompiler, get_gutter_margin_pt


def test_gutter_margin_schedule_all_boundaries():
    # Boundary and mid-range checks for the 5 KDP gutter tiers:
    # 24–150 pages -> 0.375" (27.0 pt)
    assert get_gutter_margin_pt(24) == pytest.approx(0.375 * 72.0)
    assert get_gutter_margin_pt(150) == pytest.approx(0.375 * 72.0)
    # 151–300 pages -> 0.500" (36.0 pt)
    assert get_gutter_margin_pt(151) == pytest.approx(0.500 * 72.0)
    assert get_gutter_margin_pt(300) == pytest.approx(0.500 * 72.0)
    # 301–500 pages -> 0.625" (45.0 pt)
    assert get_gutter_margin_pt(301) == pytest.approx(0.625 * 72.0)
    assert get_gutter_margin_pt(500) == pytest.approx(0.625 * 72.0)
    # 501–700 pages -> 0.750" (54.0 pt)
    assert get_gutter_margin_pt(501) == pytest.approx(0.750 * 72.0)
    assert get_gutter_margin_pt(700) == pytest.approx(0.750 * 72.0)
    # 701–828 pages -> 0.875" (63.0 pt)
    assert get_gutter_margin_pt(701) == pytest.approx(0.875 * 72.0)
    assert get_gutter_margin_pt(828) == pytest.approx(0.875 * 72.0)


def test_markdown_sanitization_xss_protection():
    malicious = "<script>alert('xss')</script><h1>Real</h1><iframe src='bad.com'></iframe><style>body{color:red}</style>Good text."
    cleaned = InteriorPDFCompiler.sanitize_markdown_text(malicious)
    assert "<script>" not in cleaned
    assert "<iframe>" not in cleaned
    assert "<style>" not in cleaned
    assert "Good text." in cleaned


def test_compile_interior_standard_6x9():
    book = Book(
        id="book-test-1",
        owner_id="user-1",
        title="Automated Cash Flow Systems",
        subtitle="The Complete Blueprint",
        topic="Personal Finance",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
        target_page_count=100,
    )
    chap1 = Chapter(
        id="chap-1",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=1,
        title="Foundations of Reserve Ratio",
        content="## Reserve Strategy\n\nMaintaining liquid reserves eliminates behavioral anxiety during market corrections.\n\n- Automate weekly sweeps.\n- Eliminate high-interest liabilities.",
    )
    chap2 = Chapter(
        id="chap-2",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=2,
        title="Execution Protocol",
        content="Deploy assets in accordance with disciplined rebalancing targets.",
    )

    req = InteriorGenerationRequest(
        include_toc=True,
        include_dedication=True,
        dedication_text="For my family and early readers.",
        is_full_bleed=False,
        font_choice="serif",
    )

    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=[chap1, chap2],
        illustrations=[],
        req=req,
    )

    assert len(pdf_bytes) > 1000
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)

    # Physical even-page check
    assert page_count % 2 == 0
    assert meta["final_even_page_count"] == page_count

    # Verify 6x9 exact MediaBox dimensions: 6 * 72 = 432 pt, 9 * 72 = 648 pt
    p1 = reader.pages[0]
    assert float(p1.mediabox.width) == 432.0
    assert float(p1.mediabox.height) == 648.0


def test_compile_interior_full_bleed():
    book = Book(
        id="book-test-2",
        owner_id="user-1",
        title="Visual Guide to Wealth",
        topic="Finance",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
        target_page_count=50,
    )
    chap = Chapter(
        id="chap-1",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=1,
        title="Intro",
        content="Full bleed graphics interior test.",
    )
    req = InteriorGenerationRequest(
        include_toc=False,
        is_full_bleed=True,
    )

    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=[chap],
        illustrations=[],
        req=req,
    )

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    p1 = reader.pages[0]
    # Full bleed 6x9 adds 0.125" to width (432 + 9 = 441 pt) and 0.25" to height (648 + 18 = 666 pt)
    assert float(p1.mediabox.width) == 441.0
    assert float(p1.mediabox.height) == 666.0


def test_interior_page_parity_blank_page_added_metadata():
    book = Book(
        id="book-parity",
        owner_id="user-1",
        title="Parity Test Book",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
    )
    # Title (1) + Copyright (2) + 1 Chapter (3) = 3 initial pages (odd)
    chap = Chapter(
        id="chap-p1",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=1,
        title="Short Chapter",
        content="Single paragraph requiring only one page.",
    )
    req = InteriorGenerationRequest(
        include_toc=False,
        include_dedication=False,
        is_full_bleed=False,
    )
    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=[chap],
        illustrations=[],
        req=req,
    )
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    # Must be padded to an even number of pages (3 -> 4)
    assert len(reader.pages) % 2 == 0
    assert meta["initial_rendered_pages"] == 3
    assert meta["final_even_page_count"] == 4
    assert meta["parity_blank_page_added"] is True


def test_unapproved_illustrations_render_placeholder_only():
    book = Book(
        id="book-unapproved",
        owner_id="user-1",
        title="Unapproved Artwork Test",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
    )
    chap = Chapter(
        id="chap-unapp-1",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=1,
        title="Chapter With Unapproved Illustration",
        content="This chapter has an unapproved illustration in GENERATED state.",
    )
    # Illustration is in GENERATED state (not APPROVED_FINAL)
    ill_unapproved = Illustration(
        id="ill-unapp-1",
        book_id=book.id,
        chapter_id=chap.id,
        owner_id="user-1",
        prompt="A high-tech digital vault with emerald glow",
        status="GENERATED",
        storage_key="illustrations/unapproved.png",
    )
    req = InteriorGenerationRequest(
        include_toc=False,
        include_dedication=False,
    )
    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=[chap],
        illustrations=[ill_unapproved],
        req=req,
    )
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    # Extract text from the PDF pages to verify the placeholder label appears
    pdf_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "[LAYOUT PLACEHOLDER: GENERATED]" in pdf_text
    assert "A high-tech digital vault" in pdf_text
    # No DPI advisory since bitmap image was not embedded
    assert len(meta["dpi_advisories"]) == 0


def test_approved_illustration_embedded_and_dpi_calculated(tmp_path, monkeypatch):
    from PIL import Image
    from app.core.config import settings

    # Setup isolated illustrations directory
    fake_storage = tmp_path / "storage"
    ill_dir = fake_storage / "illustrations"
    ill_dir.mkdir(parents=True)
    monkeypatch.setattr(settings, "STORAGE_DIR", str(fake_storage))

    # Create a 600x600 test PNG
    img_file = ill_dir / "valid_approved.png"
    img = Image.new("RGB", (600, 600), color=(30, 80, 160))
    img.save(img_file, format="PNG")

    book = Book(
        id="book-approved",
        owner_id="user-1",
        title="Approved Artwork Test",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
    )
    chap = Chapter(
        id="chap-app-1",
        book_id=book.id,
        owner_id="user-1",
        chapter_number=1,
        title="Chapter With Approved Art",
        content="This chapter contains an approved visual illustration.",
    )
    ill_approved = Illustration(
        id="ill-app-1",
        book_id=book.id,
        chapter_id=chap.id,
        owner_id="user-1",
        prompt="A beautiful compound interest chart",
        description="Figure 1: Exponential Growth Curve",
        status="APPROVED_FINAL",
        storage_key="valid_approved.png",
    )
    req = InteriorGenerationRequest(
        include_toc=False,
        include_dedication=False,
    )
    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=[chap],
        illustrations=[ill_approved],
        req=req,
    )
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pdf_text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "[LAYOUT PLACEHOLDER" not in pdf_text
    assert "Figure 1: Exponential Growth Curve" in pdf_text

    # The image is 600px rendered at 280pt = 3.888 inches -> 600 / 3.888 = ~154.3 DPI (< 300 DPI)
    # Check that DPI advisory was recorded
    assert len(meta["dpi_advisories"]) == 1
    assert meta["dpi_advisories"][0]["illustration_id"] == "ill-app-1"
    assert meta["dpi_advisories"][0]["effective_dpi"] < 300.0


def test_compile_exact_100_page_interior_and_groundwood_cover_consistency():
    """
    Publishing E2E Consistency Test:
    1. Compiles a realistic 100-page interior PDF.
    2. Verifies exact physical 100 pages, even parity without extra blank pages, and 6x9 MediaBox dimensions.
    3. Calculates full-jacket cover using the interior's verified 100 pages.
    4. Compiles Groundwood paperback cover with official 0.00235 coefficient (0.235" spine, 12.485" width).
    5. Verifies 100% font embedding and quality validation on both artifacts.
    """
    from app.services.cover_calculation import CoverCalculationService
    from app.services.cover_compiler import FullJacketCoverCompiler
    from app.schemas.book_document import CoverGenerationRequest
    from app.services.quality_validation import QualityValidationService

    book = Book(
        id="book-100-page-e2e",
        owner_id="user-publisher",
        title="Tactical Asset Allocation & Capital Preservation Systems",
        subtitle="A Comprehensive Guide to Engineering Financial Independence",
        topic="Personal Finance",
        trim_size="6x9",
        print_format="paperback",
        paper_type="groundwood",
        target_page_count=100,
    )

    # 97 chapters + Title(1) + Copyright(2) + Dedication(3) = 100 final physical pages
    chapters = [
        Chapter(
            id=f"chap-100-{i}",
            book_id=book.id,
            owner_id="user-publisher",
            chapter_number=i,
            title=f"Discipline Principle {i}: Systematic Cash Reserves",
            content=(
                f"## Capital Rule {i}\n\n"
                f"Disciplined compounding requires strict behavioral rules and automated cash sweeps. "
                f"Operating reserves must never be subordinated to speculative market timing.\n\n"
                f"- Tier 1: Immediate checking liquidity (1 month operating expenses).\n"
                f"- Tier 2: Short-term treasury ladder (5 months defensive buffer).\n"
                f"- Tier 3: Low-cost market-cap weighted index allocation."
            ),
        )
        for i in range(1, 98)
    ]

    req_interior = InteriorGenerationRequest(
        include_toc=False,
        include_dedication=True,
        dedication_text="Dedicated to rigorous allocators and patient capital.",
        is_full_bleed=False,
        font_choice="serif",
    )

    interior_bytes, int_meta = InteriorPDFCompiler.compile_interior(
        book=book,
        chapters=chapters,
        illustrations=[],
        req=req_interior,
    )

    # 1. Interior PDF Structural Verification
    int_reader = pypdf.PdfReader(io.BytesIO(interior_bytes))
    actual_pages = len(int_reader.pages)

    # Exact 100 physical pages
    assert actual_pages == 100
    assert int_meta["initial_rendered_pages"] == 100
    assert int_meta["final_even_page_count"] == 100
    assert int_meta["parity_blank_page_added"] is False  # 100 is even; no unnecessary blank page added!

    # KDP gutter schedule: 100 pages -> 0.375" (27.0 pt)
    assert int_meta["gutter_margin_pt"] == pytest.approx(27.0)
    assert int_meta["outside_margin_pt"] == pytest.approx(36.0)

    # Every single page must match exact 6x9 MediaBox: 432.0 x 648.0 pt
    for idx, page in enumerate(int_reader.pages):
        assert float(page.mediabox.width) == 432.0, f"Page {idx+1} width mismatch"
        assert float(page.mediabox.height) == 648.0, f"Page {idx+1} height mismatch"

    # Quality and font validation on interior
    int_quality = QualityValidationService.validate_pdf_structure(
        interior_bytes,
        document_type="INTERIOR",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=24,
    )
    assert int_quality["is_valid"] is True
    assert int_quality["all_fonts_embedded"] is True
    assert len(int_quality["unembedded_fonts"]) == 0

    # 2. Cover Calculation Using the Authoritative 100 Interior Pages
    calc = CoverCalculationService.calculate_paperback_cover(
        trim_size=book.trim_size,
        paper_type=book.paper_type,
        interior_page_count=actual_pages,  # STRICT SOURCE OF TRUTH: 100 pages
        is_provisional=False,
        interior_document_id="int-doc-100",
    )

    assert calc.is_provisional is False
    assert calc.is_kdp_compliant_page_count is True
    assert calc.interior_page_count == 100
    assert calc.even_page_count == 100

    # Official KDP Groundwood spine multiplier: 0.00235 inches/page
    assert calc.spine_coefficient == 0.00235
    assert calc.spine_width_inches == pytest.approx(0.235, abs=1e-4)  # 100 * 0.00235 = 0.235"
    assert calc.spine_width_pt == pytest.approx(16.92, abs=1e-2)      # 0.235 * 72 = 16.92 pt

    # Full cover width = 0.125 + 6.0 + 0.235 + 6.0 + 0.125 = 12.485" (898.92 pt)
    assert calc.full_cover_width_inches == pytest.approx(12.485, abs=1e-4)
    assert calc.full_cover_width_pt == pytest.approx(898.92, abs=1e-2)

    # Full cover height = 0.125 + 9.0 + 0.125 = 9.250" (666.0 pt)
    assert calc.full_cover_height_inches == pytest.approx(9.250, abs=1e-4)
    assert calc.full_cover_height_pt == pytest.approx(666.0, abs=1e-2)

    # Spine text eligible (100 >= 80)
    assert calc.spine_text_eligible is True

    # 3. Full-Jacket Cover Compilation
    req_cover = CoverGenerationRequest(
        custom_front_title=book.title,
        custom_front_subtitle=book.subtitle,
        custom_author_name="M. Sterling, CFP",
        back_cover_description="A mathematical manual for navigating capital allocation and financial architecture.",
        primary_color="#0f172a",
        accent_color="#f59e0b",
        include_spine_text=True,
        render_guides=False,
    )

    cover_bytes, cov_meta = FullJacketCoverCompiler.compile_cover(
        book=book,
        calc=calc,
        req=req_cover,
    )

    cov_reader = pypdf.PdfReader(io.BytesIO(cover_bytes))
    assert len(cov_reader.pages) == 1
    cov_p1 = cov_reader.pages[0]

    # Verify actual cover MediaBox matches calculated dimensions
    assert abs(float(cov_p1.mediabox.width) - float(calc.full_cover_width_pt)) < 0.1
    assert abs(float(cov_p1.mediabox.height) - float(calc.full_cover_height_pt)) < 0.1

    # Quality and font validation on cover
    cov_quality = QualityValidationService.validate_pdf_structure(
        cover_bytes,
        document_type="COVER",
        expected_width_pt=float(calc.full_cover_width_pt),
        expected_height_pt=float(calc.full_cover_height_pt),
        min_pages=1,
    )
    assert cov_quality["is_valid"] is True
    assert cov_quality["all_fonts_embedded"] is True
    assert len(cov_quality["unembedded_fonts"]) == 0


def test_weasyprint_restricted_fetcher_integration_and_blocker_reporting():
    """
    Verify WeasyPrint architecture integration:
    1. weasyprint_secure_url_fetcher blocks file:// and remote http:// protocols.
    2. If WeasyPrint C-libraries (Pango/GObject) are absent on host, the engine records
       the exact blocker and falls back to ReportLab embedded-font compiler cleanly.
    """
    from app.core.security_fetcher import weasyprint_secure_url_fetcher, SecurityFetchError

    # 1. Fetcher protocol blocking
    with pytest.raises(SecurityFetchError, match="prohibited"):
        weasyprint_secure_url_fetcher("file:///etc/shadow")

    with pytest.raises(SecurityFetchError, match="prohibited"):
        weasyprint_secure_url_fetcher("http://169.254.169.254/latest/meta-data")

    # 2. Compiler execution and blocker recording
    book = Book(
        id="book-wp-check",
        owner_id="user-wp",
        title="WeasyPrint Blocker Check",
        trim_size="6x9",
        print_format="paperback",
        paper_type="white_bw",
    )
    chap = Chapter(
        id="chap-wp-1",
        book_id=book.id,
        owner_id="user-wp",
        chapter_number=1,
        title="Intro",
        content="Testing engine execution.",
    )
    req = InteriorGenerationRequest(include_toc=False, include_dedication=False)

    pdf_bytes, meta = InteriorPDFCompiler.compile_interior(book, [chap], [], req)
    assert len(pdf_bytes) > 500

    # If WeasyPrint ran: renderer is weasyprint-css-paged-media
    # If blocked on Windows: renderer is reportlab-embedded-font-engine and weasyprint_blocker is documented
    if meta["renderer"] == "weasyprint-css-paged-media":
        assert meta["weasyprint_blocker"] is None
    else:
        assert meta["renderer"] == "reportlab-embedded-font-engine"
        assert meta["weasyprint_blocker"] is not None
        assert "cannot load library" in meta["weasyprint_blocker"] or "libgobject" in meta["weasyprint_blocker"] or "OSError" in meta["weasyprint_blocker"]
