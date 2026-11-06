import pytest
from app.schemas.kdp_validator import PrintSpecsValidationRequest
from app.services.kdp_validator import KDPValidatorService


def test_paperback_cream_paper_limit_776():
    """Verify that US 6x9 Cream Paperback strictly enforces 776 max pages."""
    # 776 pages passes
    req_valid = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="cream_bw",
        page_count=776,
    )
    res_valid = KDPValidatorService.validate_print_specs(req_valid)
    assert res_valid.is_valid is True
    assert len(res_valid.blocking_errors) == 0

    # 777 pages fails with BLOCKING_ERROR
    req_invalid = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="cream_bw",
        page_count=777,
    )
    res_invalid = KDPValidatorService.validate_print_specs(req_invalid)
    assert res_invalid.is_valid is False
    assert any("776" in e.message for e in res_invalid.blocking_errors)


def test_paperback_white_paper_limit_828():
    """Verify that US 6x9 White Paperback allows up to 828 pages."""
    req_valid = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=828,
    )
    res_valid = KDPValidatorService.validate_print_specs(req_valid)
    assert res_valid.is_valid is True

    # 829 fails
    req_invalid = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=829,
    )
    res_invalid = KDPValidatorService.validate_print_specs(req_invalid)
    assert res_invalid.is_valid is False


def test_paperback_groundwood_limits():
    """Verify groundwood limits across standard, intermediate, A4, and large trims."""
    # 5x8 groundwood max is 812
    req_5x8 = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="5x8",
        paper_type="groundwood_bw",
        page_count=812,
    )
    assert KDPValidatorService.validate_print_specs(req_5x8).is_valid is True

    req_5x8_over = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="5x8",
        paper_type="groundwood_bw",
        page_count=813,
    )
    assert KDPValidatorService.validate_print_specs(req_5x8_over).is_valid is False

    # A4 (8.27x11.69) groundwood max is 764
    req_a4 = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="8.27x11.69",
        paper_type="groundwood_bw",
        page_count=764,
    )
    assert KDPValidatorService.validate_print_specs(req_a4).is_valid is True

    # 8.5x11 groundwood max is 578
    req_85x11 = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="8.5x11",
        paper_type="groundwood_bw",
        page_count=578,
    )
    assert KDPValidatorService.validate_print_specs(req_85x11).is_valid is True


def test_hardcover_trim_and_page_limits():
    """Verify hardcover restrictions: 75-550 pages, 5 trim sizes only, prohibited papers."""
    # Valid 6x9 hardcover with 100 pages
    req_valid = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=100,
    )
    res_valid = KDPValidatorService.validate_print_specs(req_valid)
    assert res_valid.is_valid is True

    # Hardcover < 75 pages rejected
    req_under = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=74,
    )
    res_under = KDPValidatorService.validate_print_specs(req_under)
    assert res_under.is_valid is False
    assert any("75" in e.message for e in res_under.blocking_errors)

    # Hardcover > 550 pages rejected
    req_over = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=551,
    )
    res_over = KDPValidatorService.validate_print_specs(req_over)
    assert res_over.is_valid is False

    # Hardcover with unsupported trim size (e.g. 5x8) rejected
    req_bad_trim = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="5x8",
        paper_type="white_bw",
        page_count=100,
    )
    res_bad_trim = KDPValidatorService.validate_print_specs(req_bad_trim)
    assert res_bad_trim.is_valid is False
    assert any("5 trim sizes" in e.message for e in res_bad_trim.blocking_errors)

    # Hardcover with standard_color or groundwood rejected
    req_std_color = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="standard_color",
        page_count=100,
    )
    res_std_color = KDPValidatorService.validate_print_specs(req_std_color)
    assert res_std_color.is_valid is False
    assert any("prohibited for hardcover" in e.message for e in res_std_color.blocking_errors)


def test_hardcover_marketplace_rules():
    """Verify primary, secondary, and unsupported hardcover marketplace tiers."""
    # Japan (amazon_co_jp) is explicitly unsupported
    req_jp = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=100,
        marketplace="amazon_co_jp",
    )
    res_jp = KDPValidatorService.validate_print_specs(req_jp)
    assert res_jp.is_valid is False
    assert any("not supported on Amazon JP" in e.message for e in res_jp.blocking_errors)

    # Australia (amazon_com_au) is secondary distribution -> Advisory warning, not blocking
    req_au = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=100,
        marketplace="amazon_com_au",
    )
    res_au = KDPValidatorService.validate_print_specs(req_au)
    assert res_au.is_valid is True
    assert any("not a primary hardcover distribution marketplace" in w.message for w in res_au.advisory_warnings)


def test_unverified_trim_emits_advisory_without_fabricated_limits():
    """Verify that undocumented custom trim sizes emit advisory warnings without generic limits."""
    req_custom = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="7.77x9.99",
        paper_type="white_bw",
        page_count=100,
    )
    res_custom = KDPValidatorService.validate_print_specs(req_custom)
    assert res_custom.is_valid is True
    assert len(res_custom.blocking_errors) == 0
    assert any("unverified in KDP OS v1.0" in w.message for w in res_custom.advisory_warnings)


def test_format_aware_gutter_margins():
    """Verify format-aware gutter margin tiers."""
    # Paperback: 200 pages requires 0.500" gutter
    req_pb = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=200,
        inside_margin_in=0.45,
    )
    res_pb = KDPValidatorService.validate_print_specs(req_pb)
    assert res_pb.is_valid is False
    assert any("0.5" in e.message for e in res_pb.blocking_errors)

    # Paperback: 0.50" gutter on 200 pages passes
    req_pb_ok = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=200,
        inside_margin_in=0.50,
    )
    assert KDPValidatorService.validate_print_specs(req_pb_ok).is_valid is True

    # Hardcover: 520 pages requires 0.750" gutter (does not evaluate 701-828 tier)
    req_hc = PrintSpecsValidationRequest(
        print_format="hardcover",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=520,
        inside_margin_in=0.70,
    )
    res_hc = KDPValidatorService.validate_print_specs(req_hc)
    assert res_hc.is_valid is False
    assert any("0.75" in e.message for e in res_hc.blocking_errors)


def test_all_79_paperback_combinations_validated():
    """Verify that every one of the 79 normalized paperback records matches exactly and enforces limits."""
    spec = KDPValidatorService.get_raw_spec()
    pb_specs = spec.get("paperback_specifications", [])
    assert len(pb_specs) == 79, f"Expected 79 paperback specifications, found {len(pb_specs)}"

    for record in pb_specs:
        trim = record["trim_size_name"]
        paper = record["paper_type"]
        min_p = record["min_pages"]
        max_p = record["max_pages"]
        spec_id = record["spec_id"]

        # 1. min_pages valid
        res_min = KDPValidatorService.validate_print_specs(
            PrintSpecsValidationRequest(
                print_format="paperback",
                trim_size=trim,
                paper_type=paper,
                page_count=min_p,
            )
        )
        assert res_min.is_valid is True, f"Failed at min_pages for {spec_id}"
        assert res_min.matched_specification["spec_id"] == spec_id

        # 2. max_pages valid
        res_max = KDPValidatorService.validate_print_specs(
            PrintSpecsValidationRequest(
                print_format="paperback",
                trim_size=trim,
                paper_type=paper,
                page_count=max_p,
            )
        )
        assert res_max.is_valid is True, f"Failed at max_pages for {spec_id}"
        assert res_max.matched_specification["spec_id"] == spec_id

        # 3. max_pages + 1 rejected
        res_over = KDPValidatorService.validate_print_specs(
            PrintSpecsValidationRequest(
                print_format="paperback",
                trim_size=trim,
                paper_type=paper,
                page_count=max_p + 1,
            )
        )
        assert res_over.is_valid is False, f"Failed to reject max_pages+1 for {spec_id}"
        assert any(e.rule_id == "KDP-PRN-001" for e in res_over.blocking_errors)


def test_all_15_hardcover_combinations_and_spec_ids():
    """Verify all 15 hardcover combinations match and return their exact spec_id from hardcover_technical_matrix."""
    spec = KDPValidatorService.get_raw_spec()
    hc_matrix = spec.get("hardcover_technical_matrix", [])
    assert len(hc_matrix) == 15, f"Expected 15 hardcover combinations, found {len(hc_matrix)}"

    for record in hc_matrix:
        trim = record["trim_size_name"]
        paper = record["paper_type"]
        expected_id = record["spec_id"]

        res = KDPValidatorService.validate_print_specs(
            PrintSpecsValidationRequest(
                print_format="hardcover",
                trim_size=trim,
                paper_type=paper,
                page_count=100,
            )
        )
        assert res.is_valid is True, f"Hardcover combination {trim} + {paper} failed validation"
        assert res.matched_specification is not None
        assert res.matched_specification["spec_id"] == expected_id
        assert res.matched_specification["min_pages"] == 75
        assert res.matched_specification["max_pages"] == 550


def test_gutter_validation_above_828_pages():
    """Verify gutter validation behavior for page counts exceeding maximum supported paperback tier."""
    # 850 pages: page-limit violation is blocking
    req_over = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=850,
        inside_margin_in=0.50,  # Below 0.875" max tier
    )
    res_over = KDPValidatorService.validate_print_specs(req_over)
    assert res_over.is_valid is False
    assert any(e.rule_id == "KDP-PRN-001" for e in res_over.blocking_errors)
    assert any(w.rule_id == "KDP-PRN-002" and "0.875" in w.message for w in res_over.advisory_warnings)

    # 850 pages with gutter meeting max tier (0.875") -> still blocked by page limit, but no spurious gutter advisory
    req_over_gutter_ok = PrintSpecsValidationRequest(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        page_count=850,
        inside_margin_in=0.875,
    )
    res_gutter_ok = KDPValidatorService.validate_print_specs(req_over_gutter_ok)
    assert res_gutter_ok.is_valid is False
    assert any(e.rule_id == "KDP-PRN-001" for e in res_gutter_ok.blocking_errors)
    assert not any("gutter" in w.message.lower() for w in res_gutter_ok.advisory_warnings)
