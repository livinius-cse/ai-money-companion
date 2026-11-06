import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from app.schemas.kdp_validator import (
    PrintSpecsValidationRequest,
    MetadataValidationRequest,
    ValidationResultResponse,
    RuleViolation,
)
from app.services.html_validator import HTMLAllowlistValidator

SPEC_FILE_PATH = Path(__file__).resolve().parent.parent / "kdp_specs" / "kdp_print_spec_v2.json"

_CACHED_SPEC: Optional[Dict[str, Any]] = None


def get_cached_kdp_spec() -> Dict[str, Any]:
    global _CACHED_SPEC
    if _CACHED_SPEC is None:
        with open(SPEC_FILE_PATH, "r", encoding="utf-8") as f:
            _CACHED_SPEC = json.load(f)
    return _CACHED_SPEC


class KDPValidatorService:
    """
    Authoritative KDP Specification validation engine.
    Validates print specifications, gutter/outside margins, spine thresholds,
    and metadata against verified Amazon KDP documentation.
    """

    @classmethod
    def get_raw_spec(cls) -> Dict[str, Any]:
        return get_cached_kdp_spec()

    @staticmethod
    def calculate_applicable_pages(planned_pages: int) -> int:
        """KDP rounds an odd interior page count up to the nearest even number of whole sheets."""
        if planned_pages <= 0:
            return 0
        return planned_pages + (1 if planned_pages % 2 != 0 else 0)

    @staticmethod
    def calculate_spine_width(page_count: int, paper_type: str) -> float:
        """Calculate estimated spine width in inches using official multiplier approximations."""
        multipliers = {
            "white_bw": 0.002252,
            "cream_bw": 0.002500,
            "groundwood_bw": 0.002347,
            "standard_color": 0.002252,
            "premium_color": 0.002347,
        }
        mult = multipliers.get(paper_type, 0.002252)
        return round(page_count * mult, 4)

    @classmethod
    def validate_print_specs(cls, req: PrintSpecsValidationRequest) -> ValidationResultResponse:
        spec = cls.get_raw_spec()
        blocking: List[RuleViolation] = []
        advisories: List[RuleViolation] = []
        matched_spec: Optional[Dict[str, Any]] = None

        applicable_pages = cls.calculate_applicable_pages(req.page_count)
        calc_spine = cls.calculate_spine_width(applicable_pages, req.paper_type)
        spine_allowed = applicable_pages >= 80

        # Normalization helpers
        req_trim = req.trim_size.strip().lower().replace(" ", "").replace('"', '')

        # -------------------------------------------------------------
        # 1. FORMAT SPECIFIC VALIDATION
        # -------------------------------------------------------------
        if req.print_format == "paperback":
            # Exact-record matching in 44 normalized paperback records
            pb_specs = spec.get("paperback_specifications", [])
            for p in pb_specs:
                p_trim = p["trim_size_name"].strip().lower().replace(" ", "").replace('"', '')
                if p_trim == req_trim and p["paper_type"] == req.paper_type:
                    matched_spec = p
                    break

            if matched_spec:
                min_p = matched_spec["min_pages"]
                max_p = matched_spec["max_pages"]
                if req.page_count < min_p:
                    blocking.append(
                        RuleViolation(
                            rule_id="KDP-PRN-001",
                            field="page_count",
                            severity="BLOCKING_ERROR",
                            message=f"Page count ({req.page_count}) is below minimum {min_p} pages for paperback trim {matched_spec['trim_size_name']} ({matched_spec['paper_weight_desc']}).",
                            reference_doc=matched_spec["source_url"],
                        )
                    )
                elif req.page_count > max_p:
                    blocking.append(
                        RuleViolation(
                            rule_id="KDP-PRN-001",
                            field="page_count",
                            severity="BLOCKING_ERROR",
                            message=f"Page count ({req.page_count}) exceeds maximum {max_p} pages for paperback trim {matched_spec['trim_size_name']} ({matched_spec['paper_weight_desc']}).",
                            reference_doc=matched_spec["source_url"],
                        )
                    )
            else:
                # Unsupported or unverified combination -> Advisory warning (ZERO fabricated limits)
                advisories.append(
                    RuleViolation(
                        rule_id="KDP-SPEC-UNVERIFIED",
                        field="trim_size",
                        severity="ADVISORY_WARNING",
                        message=(
                            f"The selected combination (Format: paperback, Trim: {req.trim_size}, "
                            f"Paper: {req.paper_type}, Market: {req.marketplace}) is unverified in KDP OS v1.0. "
                            f"Please verify exact page limits directly on Amazon KDP setup."
                        ),
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/G201857950",
                    )
                )

        elif req.print_format == "hardcover":
            hc_model = spec.get("hardcover_specification_model", {})

            # Check marketplace tier
            market_lower = req.marketplace.strip().lower()
            if market_lower in hc_model.get("explicitly_unsupported_marketplaces", []):
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="marketplace",
                        severity="BLOCKING_ERROR",
                        message=f"Hardcover printing and distribution is not supported on Amazon JP ({req.marketplace}).",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GAVW3FZZAKA2KY3B",
                    )
                )
            elif market_lower in hc_model.get("secondary_distribution_marketplaces", []):
                advisories.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="marketplace",
                        severity="ADVISORY_WARNING",
                        message=f"{req.marketplace} is not a primary hardcover distribution marketplace; to make hardcover available there, your book must be available on Amazon.com.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GAVW3FZZAKA2KY3B",
                    )
                )
            elif market_lower not in hc_model.get("primary_marketplaces", []):
                advisories.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="marketplace",
                        severity="ADVISORY_WARNING",
                        message=f"Hardcover availability for marketplace '{req.marketplace}' is undocumented in KDP OS v1.0. Please verify on official KDP portal.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GAVW3FZZAKA2KY3B",
                    )
                )

            # Check prohibited paper options
            if req.paper_type in hc_model.get("prohibited_ink_paper", []):
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="paper_type",
                        severity="BLOCKING_ERROR",
                        message=f"Paper/ink option '{req.paper_type}' is prohibited for hardcover on Amazon KDP. (Supported: white_bw, cream_bw, premium_color).",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GAVW3FZZAKA2KY3B",
                    )
                )

            # Check supported trim sizes
            supported_hc_trims = [t.lower().replace("x", "") for t in hc_model.get("supported_trim_sizes", [])]
            req_trim_clean = req_trim.replace("x", "")
            if not any(req_trim_clean == st for st in supported_hc_trims):
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="trim_size",
                        severity="BLOCKING_ERROR",
                        message=f"Hardcover is officially supported only on 5 trim sizes (5.5x8.5, 6x9, 6.14x9.21, 7x10, 8.25x11). Trim '{req.trim_size}' is unsupported.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                    )
                )

            # Check page count boundaries (75 to 550)
            min_hc = hc_model.get("min_pages", 75)
            max_hc = hc_model.get("max_pages", 550)
            if req.page_count < min_hc:
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="page_count",
                        severity="BLOCKING_ERROR",
                        message=f"Hardcover page count ({req.page_count}) is below official minimum of {min_hc} pages.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                    )
                )
            elif req.page_count > max_hc:
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-005",
                        field="page_count",
                        severity="BLOCKING_ERROR",
                        message=f"Hardcover page count ({req.page_count}) exceeds official maximum of {max_hc} pages.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                    )
                )
            else:
                hc_tech_matrix = spec.get("hardcover_technical_matrix", [])
                hc_spec_id = None
                for h in hc_tech_matrix:
                    h_trim = h.get("trim_size_name", "").strip().lower().replace(" ", "").replace('"', '')
                    if (h_trim == req_trim or h_trim.replace("x", "") == req_trim_clean) and h.get("paper_type") == req.paper_type:
                        hc_spec_id = h.get("spec_id")
                        break

                matched_spec = {
                    "format": "hardcover",
                    "trim_size": req.trim_size,
                    "paper_type": req.paper_type,
                    "min_pages": min_hc,
                    "max_pages": max_hc,
                    "spec_id": hc_spec_id,
                }

        # -------------------------------------------------------------
        # 2. FORMAT-AWARE GUTTER MARGIN VALIDATION
        # -------------------------------------------------------------
        if req.inside_margin_in is not None:
            gutter_tiers = spec.get("gutter_margins", {}).get(req.print_format, [])
            required_gutter: Optional[float] = None
            for tier in gutter_tiers:
                if tier["min_pages"] <= applicable_pages <= tier["max_pages"]:
                    required_gutter = tier["margin_in"]
                    break

            if required_gutter is not None:
                if req.inside_margin_in < required_gutter:
                    rule_code = "KDP-PRN-002" if req.print_format == "paperback" else "KDP-PRN-003"
                    blocking.append(
                        RuleViolation(
                            rule_id=rule_code,
                            field="inside_margin_in",
                            severity="BLOCKING_ERROR",
                            message=(
                                f"Inside (gutter) margin {req.inside_margin_in} in is below required "
                                f"{required_gutter} in for {req.print_format} with {applicable_pages} applicable pages."
                            ),
                            reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                        )
                    )
            elif applicable_pages > 0 and gutter_tiers:
                # If page count exceeds the maximum supported tier in the specification,
                # the page-count ceiling violation is already flagged as BLOCKING_ERROR in step 1.
                # Gutter evaluation produces a consistent advisory against the highest verified tier
                # without inventing non-existent KDP tiers.
                max_tier = max(gutter_tiers, key=lambda t: t["max_pages"])
                if applicable_pages > max_tier["max_pages"] and req.inside_margin_in < max_tier["margin_in"]:
                    advisories.append(
                        RuleViolation(
                            rule_id="KDP-PRN-002" if req.print_format == "paperback" else "KDP-PRN-003",
                            field="inside_margin_in",
                            severity="ADVISORY_WARNING",
                            message=(
                                f"Page count ({applicable_pages}) exceeds maximum verified KDP gutter tier ({max_tier['max_pages']} pages). "
                                f"Gutter margin {req.inside_margin_in} in is below the highest standard tier minimum of {max_tier['margin_in']} in."
                            ),
                            reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                        )
                    )

        # -------------------------------------------------------------
        # 3. OUTSIDE MARGIN VALIDATION
        # -------------------------------------------------------------
        if req.outside_margin_in is not None:
            required_outside = 0.375 if req.has_bleed else 0.250
            if req.outside_margin_in < required_outside:
                blocking.append(
                    RuleViolation(
                        rule_id="KDP-PRN-004",
                        field="outside_margin_in",
                        severity="BLOCKING_ERROR",
                        message=(
                            f"Outside margin {req.outside_margin_in} in is below minimum required "
                            f"{required_outside} in ({'with bleed' if req.has_bleed else 'without bleed'})."
                        ),
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6",
                    )
                )

        return ValidationResultResponse(
            is_valid=(len(blocking) == 0),
            blocking_errors=blocking,
            advisory_warnings=advisories,
            applicable_page_count=applicable_pages,
            calculated_spine_width_in=calc_spine,
            spine_text_allowed=spine_allowed,
            matched_specification=matched_spec,
        )

    @classmethod
    def validate_metadata(cls, req: MetadataValidationRequest) -> ValidationResultResponse:
        spec = cls.get_raw_spec()
        blocking: List[RuleViolation] = []
        advisories: List[RuleViolation] = []

        # 1. Combined title and subtitle <= 200 chars
        total_title_len = len(req.title) + (len(req.subtitle) if req.subtitle else 0)
        if total_title_len > 200:
            blocking.append(
                RuleViolation(
                    rule_id="KDP-META-001",
                    field="title",
                    severity="BLOCKING_ERROR",
                    message=f"Combined title and subtitle ({total_title_len} chars) exceeds official KDP maximum of 200 characters.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/GW7J4WEKBVU25YEC",
                )
            )

        # 2. Keywords slots <= 7
        if len(req.keywords) > 7:
            blocking.append(
                RuleViolation(
                    rule_id="KDP-META-003",
                    field="keywords",
                    severity="BLOCKING_ERROR",
                    message=f"Keyword slots count ({len(req.keywords)}) exceeds official KDP maximum of 7 fields.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201298500",
                )
            )

        # Keyword length and title-word repetition advisories
        title_words = set(w.lower() for w in req.title.split() if len(w) > 3)
        for idx, kw in enumerate(req.keywords, start=1):
            if len(kw) > 50:
                advisories.append(
                    RuleViolation(
                        rule_id="KDP-ADV-001",
                        field=f"keywords[{idx}]",
                        severity="ADVISORY_WARNING",
                        message=f"Keyword phrase '{kw[:30]}...' ({len(kw)} chars) exceeds the 50-character advisory threshold.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/G201298500",
                    )
                )
            kw_words = set(w.lower() for w in kw.split())
            repeated = title_words.intersection(kw_words)
            if repeated:
                advisories.append(
                    RuleViolation(
                        rule_id="KDP-ADV-002",
                        field=f"keywords[{idx}]",
                        severity="ADVISORY_WARNING",
                        message=f"Keyword phrase '{kw}' repeats title words {repeated}. Amazon indexes title words automatically.",
                        reference_doc="https://kdp.amazon.com/en_US/help/topic/G201298500",
                    )
                )

        # 3. HTML description validation
        html_violations = HTMLAllowlistValidator.validate_description(req.description_html)
        blocking.extend(html_violations)

        return ValidationResultResponse(
            is_valid=(len(blocking) == 0),
            blocking_errors=blocking,
            advisory_warnings=advisories,
            applicable_page_count=0,
            calculated_spine_width_in=None,
            spine_text_allowed=False,
            matched_specification=None,
        )
