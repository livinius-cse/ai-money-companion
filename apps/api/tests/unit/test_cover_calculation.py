import pytest
from app.services.cover_calculation import (
    CoverCalculationService,
    SPINE_COEFFICIENTS,
    parse_trim_size_inches,
)


def test_parse_trim_size_inches():
    w, h = parse_trim_size_inches("6x9")
    assert float(w) == 6.0
    assert float(h) == 9.0

    w, h = parse_trim_size_inches("5.5x8.5")
    assert float(w) == 5.5
    assert float(h) == 8.5

    w, h = parse_trim_size_inches("8.5x11 in")
    assert float(w) == 8.5
    assert float(h) == 11.0

    with pytest.raises(ValueError):
        parse_trim_size_inches("invalid")


def test_paperback_spine_coefficients():
    # Verify all 5 official KDP paper type coefficients are present
    assert float(SPINE_COEFFICIENTS["white_bw"]) == 0.002252
    assert float(SPINE_COEFFICIENTS["cream_bw"]) == 0.0025
    assert float(SPINE_COEFFICIENTS["groundwood"]) == 0.00235
    assert float(SPINE_COEFFICIENTS["standard_color"]) == 0.002252
    assert float(SPINE_COEFFICIENTS["premium_color"]) == 0.002347


def test_paperback_cover_formula_exact_6x9_100_pages():
    calc = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=100,
    )
    # 100 pages * 0.002252 = 0.2252 inches
    assert round(calc.spine_width_inches, 4) == 0.2252
    assert round(calc.spine_width_pt, 2) == round(0.2252 * 72.0, 2)

    # Full width = 0.125 (left bleed) + 6.0 (back) + 0.2252 (spine) + 6.0 (front) + 0.125 (right bleed)
    # = 12.4752 inches = 898.2144 pt
    assert round(calc.full_cover_width_inches, 4) == 12.4752
    assert round(calc.full_cover_width_pt, 2) == round(12.4752 * 72.0, 2)

    # Full height = 0.125 (top bleed) + 9.0 (trim) + 0.125 (bottom bleed) = 9.25 inches = 666.0 pt
    assert calc.full_cover_height_inches == 9.25
    assert calc.full_cover_height_pt == 666.0


def test_odd_to_even_page_rounding():
    # Odd page count 101 must be physically rounded to 102 for spine calculation
    calc_odd = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=101,
    )
    calc_even = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=102,
    )
    assert calc_odd.even_page_count == 102
    assert calc_odd.spine_width_inches == calc_even.spine_width_inches
    assert calc_odd.full_cover_width_inches == calc_even.full_cover_width_inches


def test_spine_text_threshold_79_vs_80():
    # 78 pages (even) -> ineligible
    calc_78 = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=78,
    )
    assert calc_78.spine_text_eligible is False
    assert "under 80 pages" in calc_78.spine_text_reason

    # 79 pages -> rounds up to 80 -> eligible!
    calc_79 = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=79,
    )
    assert calc_79.even_page_count == 80
    assert calc_79.spine_text_eligible is True

    # 80 pages -> eligible
    calc_80 = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=80,
    )
    assert calc_80.spine_text_eligible is True
    assert calc_80.spine_text_reason is None


def test_hardcover_case_laminate_geometry():
    calc = CoverCalculationService.calculate_hardcover_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=120,
    )
    assert calc.format == "hardcover"
    assert calc.bleed_inches == 0.51  # 0.51" case-laminate wrap
    assert calc.safe_zone_margin_inches == 0.635  # 0.635" safe distance
    # Full cover width includes 2 * 0.51" wrap
    assert calc.full_cover_width_inches > 13.0
    # Must be explicitly marked as restricted and unsupported without verified KDP template
    assert calc.is_supported is False
    assert calc.restriction_reason is not None
    assert "restricted" in calc.restriction_reason.lower()


def test_groundwood_official_kdp_coefficient_regression():
    """
    Definite defect regression test:
    Verify Groundwood paper uses 0.00235 in/page per Amazon KDP official spec.
    At 100 pages:
      Spine width must be exactly 0.2350 inches (NOT 0.2252 and NOT 0.2347).
      Full cover width for 6x9 = 0.125 + 6.0 + 0.235 + 6.0 + 0.125 = 12.4850 inches.
    """
    # Test with both "groundwood" and "groundwood_bw"
    for p_type in ["groundwood", "groundwood_bw"]:
        calc = CoverCalculationService.calculate_paperback_cover(
            trim_size="6x9",
            paper_type=p_type,
            interior_page_count=100,
        )
        assert calc.spine_coefficient == 0.00235
        assert round(calc.spine_width_inches, 4) == 0.2350
        # Specifically verify it does NOT equal the incorrect values
        assert calc.spine_width_inches != 0.2252
        assert calc.spine_width_inches != 0.2347

        # Full cover width check: 0.125 + 6.0 + 0.235 + 6.0 + 0.125 = 12.4850
        assert round(calc.full_cover_width_inches, 4) == 12.4850
        assert round(calc.full_cover_width_pt, 2) == round(12.4850 * 72.0, 2)


def test_all_five_kdp_paperback_coefficients_at_100_pages():
    """Regression test verifying all 5 official Amazon KDP paper types."""
    expected_spines = {
        "white_bw": 0.2252,
        "cream_bw": 0.2500,
        "groundwood": 0.2350,
        "standard_color": 0.2252,
        "premium_color": 0.2347,
    }
    for paper, expected_spine in expected_spines.items():
        calc = CoverCalculationService.calculate_paperback_cover(
            trim_size="6x9",
            paper_type=paper,
            interior_page_count=100,
        )
        assert round(calc.spine_width_inches, 4) == expected_spine, f"Failed for {paper}"
        expected_width = round(0.125 + 6.0 + expected_spine + 6.0 + 0.125, 4)
        assert round(calc.full_cover_width_inches, 4) == expected_width, f"Width mismatch for {paper}"
        assert calc.is_supported is True


def test_paperback_provisional_vs_authoritative_calculation():
    """Verify provisional vs authoritative calculation metadata."""
    # Provisional calculation without interior PDF
    calc_prov = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="groundwood",
        interior_page_count=100,
        is_provisional=True,
    )
    assert calc_prov.is_provisional is True
    assert "Provisional" in calc_prov.provenance

    # Authoritative calculation with compiled interior PDF
    calc_auth = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="groundwood",
        interior_page_count=100,
        is_provisional=False,
        interior_document_id="doc-int-100",
    )
    assert calc_auth.is_provisional is False
    assert calc_auth.interior_document_id == "doc-int-100"
    assert "Authoritative" in calc_auth.provenance


def test_below_24_pages_minimum_kdp_threshold():
    """Verify calculation flags page count below KDP 24-page physical minimum."""
    calc_6 = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=6,
    )
    assert calc_6.is_kdp_compliant_page_count is False
    assert "at least 24 pages" in calc_6.min_page_warning

    calc_24 = CoverCalculationService.calculate_paperback_cover(
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=24,
    )
    assert calc_24.is_kdp_compliant_page_count is True
    assert calc_24.min_page_warning is None
