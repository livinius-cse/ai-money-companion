import pytest
from app.services.kdp_validator import KDPValidatorService
from app.schemas.kdp_validator import PrintSpecsValidationRequest


def test_spine_threshold_odd_to_even_rounding():
    """
    Verify conservative 80-page spine text threshold:
    - 78 planned pages remains 78 applicable pages -> spine text prohibited.
    - 79 planned pages rounds up to 80 applicable pages -> spine text allowed.
    """
    # 78 pages
    req_78 = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=78,
    )
    res_78 = KDPValidatorService.validate_print_specs(req_78)
    assert res_78.applicable_page_count == 78
    assert res_78.spine_text_allowed is False

    # 79 pages -> rounds to 80 applicable pages
    req_79 = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=79,
    )
    res_79 = KDPValidatorService.validate_print_specs(req_79)
    assert res_79.applicable_page_count == 80
    assert res_79.spine_text_allowed is True


def test_spine_width_calculation():
    """Verify spine width calculation formulas for white, cream, groundwood, and color."""
    # 100 pages white B&W: 100 * 0.002252 = 0.2252
    w_white = KDPValidatorService.calculate_spine_width(100, "white_bw")
    assert w_white == 0.2252

    # 100 pages cream B&W: 100 * 0.002500 = 0.2500
    w_cream = KDPValidatorService.calculate_spine_width(100, "cream_bw")
    assert w_cream == 0.2500

    # 100 pages groundwood B&W: 100 * 0.002347 = 0.2347
    w_gw = KDPValidatorService.calculate_spine_width(100, "groundwood_bw")
    assert w_gw == 0.2347
