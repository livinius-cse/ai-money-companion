import decimal
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Tuple, Optional
from app.schemas.book_document import CoverCalculationResponse

# Official Amazon KDP Spine Thickness Coefficients (inches per page)
# Provenance: Amazon KDP Print Options & Cover Calculator Specification (kdp.amazon.com/en_US/help/topic/G201953020)
SPINE_COEFFICIENTS: Dict[str, Decimal] = {
    "white_bw": Decimal("0.002252"),       # Black & White on White paper
    "cream_bw": Decimal("0.0025"),          # Black & White on Cream paper
    "groundwood": Decimal("0.00235"),       # Black & White on Groundwood paper (official KDP: 0.00235 in/page)
    "groundwood_bw": Decimal("0.00235"),    # Alias for Groundwood B&W
    "standard_color": Decimal("0.002252"),  # Standard Color on White paper
    "premium_color": Decimal("0.002347"),   # Premium Color on White paper
}

POINTS_PER_INCH = Decimal("72.0")
PAPERBACK_BLEED_INCHES = Decimal("0.125")
PAPERBACK_SAFE_MARGIN_INCHES = Decimal("0.125")
SPINE_TEXT_MIN_PAGE_THRESHOLD = 80

# Hardcover Case-Laminate Constants
# Provenance: Amazon KDP Hardcover Cover Specifications (kdp.amazon.com/en_US/help/topic/G7S2GFJ6TP9A7F3H)
HARDCOVER_WRAP_INCHES = Decimal("0.51")
HARDCOVER_SAFE_DISTANCE_INCHES = Decimal("0.635")
HARDCOVER_HINGE_INCHES = Decimal("0.40")
HARDCOVER_BOARD_ALLOWANCE_INCHES = Decimal("0.120")


def parse_trim_size_inches(trim_size: str) -> Tuple[Decimal, Decimal]:
    """Parse trim size string like '6x9' or '5.5x8.5' into (width, height) in inches."""
    clean = trim_size.lower().replace("in", "").strip()
    parts = clean.split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid trim size format '{trim_size}'. Expected format 'WxH' (e.g. '6x9').")
    try:
        return Decimal(parts[0].strip()), Decimal(parts[1].strip())
    except Exception as e:
        raise ValueError(f"Could not parse numeric dimensions from trim size '{trim_size}': {e}")


class CoverCalculationService:
    """
    Deterministic mathematics engine for Amazon KDP full-jacket cover calculations.
    Uses exact Decimal arithmetic to eliminate floating-point drift.
    """

    @classmethod
    def calculate_paperback_cover(
        cls,
        trim_size: str,
        paper_type: str,
        interior_page_count: int,
        is_provisional: bool = False,
        interior_document_id: Optional[str] = None,
    ) -> CoverCalculationResponse:
        """
        Calculate paperback full-jacket dimensions, spine thickness, safe zones, and barcode box.
        Formula:
          Total Width = Bleed (0.125) + Back Cover Width + Spine Width + Front Cover Width + Bleed (0.125)
          Total Height = Bleed (0.125) + Trim Height + Bleed (0.125)
        """
        trim_w, trim_h = parse_trim_size_inches(trim_size)

        # 1. KDP two-sided sheet rounding
        even_pages = interior_page_count if interior_page_count % 2 == 0 else interior_page_count + 1
        is_kdp_compliant = even_pages >= 24
        min_warning = None if is_kdp_compliant else (
            f"Amazon KDP requires at least 24 pages for paperback printing. Current interior has only {even_pages} pages."
        )

        # 2. Spine coefficient
        norm_paper = paper_type.lower().strip()
        if norm_paper in ("groundwood", "groundwood_bw", "groundwood-bw"):
            norm_paper = "groundwood"
        elif norm_paper in ("white", "white_bw", "white-bw"):
            norm_paper = "white_bw"
        elif norm_paper in ("cream", "cream_bw", "cream-bw"):
            norm_paper = "cream_bw"
        elif norm_paper in ("standard", "standard_color", "standard-color"):
            norm_paper = "standard_color"
        elif norm_paper in ("premium", "premium_color", "premium-color", "color"):
            norm_paper = "premium_color"
        elif norm_paper not in SPINE_COEFFICIENTS:
            norm_paper = "white_bw"
        coeff = SPINE_COEFFICIENTS[norm_paper]

        # 3. Spine width
        spine_width_in = (Decimal(even_pages) * coeff).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        spine_width_pt = (spine_width_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 4. Full cover dimensions
        full_width_in = (PAPERBACK_BLEED_INCHES + trim_w + spine_width_in + trim_w + PAPERBACK_BLEED_INCHES).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        full_height_in = (PAPERBACK_BLEED_INCHES + trim_h + PAPERBACK_BLEED_INCHES).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        full_width_pt = (full_width_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        full_height_pt = (full_height_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # 5. Spine text eligibility (minimum 80 pages)
        spine_text_eligible = even_pages >= SPINE_TEXT_MIN_PAGE_THRESHOLD
        reason = None
        if not spine_text_eligible:
            reason = (
                f"Page count is {even_pages} (under {SPINE_TEXT_MIN_PAGE_THRESHOLD} pages). "
                f"Amazon KDP prohibits spine text on volumes below 80 pages to prevent font fold-over."
            )

        # 6. Barcode clearance area (2.0" wide x 1.2" high, located on lower right of back cover)
        # Position relative to bottom-left origin in points
        bleed_pt = float(PAPERBACK_BLEED_INCHES * POINTS_PER_INCH)
        back_width_pt = float(trim_w * POINTS_PER_INCH)
        barcode_w_pt = 144.0  # 2.0 inches
        barcode_h_pt = 86.4   # 1.2 inches
        # 0.25" (18pt) clearance from spine fold line, 0.25" from bottom trim
        barcode_x = bleed_pt + back_width_pt - barcode_w_pt - 18.0
        barcode_y = bleed_pt + 18.0

        prov_text = (
            "Provisional calculation based on target page count. Final spine width and cover dimensions require compiling the interior PDF first."
            if is_provisional
            else f"Authoritative calculation based on compiled interior PDF ({even_pages} pages). Provenance: Amazon KDP Paperback Cover Specification (kdp.amazon.com/en_US/help/topic/G201953020)"
        )

        return CoverCalculationResponse(
            format="paperback",
            trim_size=trim_size,
            paper_type=norm_paper,
            interior_page_count=interior_page_count,
            even_page_count=even_pages,
            spine_coefficient=float(coeff),
            spine_width_inches=float(spine_width_in),
            spine_width_pt=float(spine_width_pt),
            full_cover_width_inches=float(full_width_in),
            full_cover_width_pt=float(full_width_pt),
            full_cover_height_inches=float(full_height_in),
            full_cover_height_pt=float(full_height_pt),
            bleed_inches=float(PAPERBACK_BLEED_INCHES),
            bleed_pt=float(PAPERBACK_BLEED_INCHES * POINTS_PER_INCH),
            safe_zone_margin_inches=float(PAPERBACK_SAFE_MARGIN_INCHES),
            safe_zone_margin_pt=float(PAPERBACK_SAFE_MARGIN_INCHES * POINTS_PER_INCH),
            spine_text_eligible=spine_text_eligible,
            spine_text_reason=reason,
            barcode_box={
                "x_pt": barcode_x,
                "y_pt": barcode_y,
                "width_pt": barcode_w_pt,
                "height_pt": barcode_h_pt,
            },
            provenance=prov_text,
            is_supported=True,
            restriction_reason=None,
            is_provisional=is_provisional,
            interior_document_id=interior_document_id,
            is_kdp_compliant_page_count=is_kdp_compliant,
            min_page_warning=min_warning,
        )

    @classmethod
    def calculate_hardcover_cover(
        cls,
        trim_size: str,
        paper_type: str,
        interior_page_count: int,
    ) -> CoverCalculationResponse:
        """
        Calculate hardcover (case-laminate) full-jacket dimensions with 0.51" wrap and hinge allowances.
        """
        trim_w, trim_h = parse_trim_size_inches(trim_size)
        even_pages = interior_page_count if interior_page_count % 2 == 0 else interior_page_count + 1

        norm_paper = paper_type.lower().strip()
        if norm_paper in ("groundwood", "groundwood_bw", "groundwood-bw"):
            norm_paper = "groundwood"
        elif norm_paper in ("white", "white_bw", "white-bw"):
            norm_paper = "white_bw"
        elif norm_paper in ("cream", "cream_bw", "cream-bw"):
            norm_paper = "cream_bw"
        elif norm_paper in ("standard", "standard_color", "standard-color"):
            norm_paper = "standard_color"
        elif norm_paper in ("premium", "premium_color", "premium-color", "color"):
            norm_paper = "premium_color"
        elif norm_paper not in SPINE_COEFFICIENTS:
            norm_paper = "white_bw"
        coeff = SPINE_COEFFICIENTS[norm_paper]

        # Spine includes paper pages + hardcover board allowance
        raw_spine_in = (Decimal(even_pages) * coeff).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        spine_width_in = (raw_spine_in + HARDCOVER_BOARD_ALLOWANCE_INCHES).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        spine_width_pt = (spine_width_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Full cover with 0.51" case-laminate wrap on top/bottom/sides
        full_width_in = (HARDCOVER_WRAP_INCHES + trim_w + spine_width_in + trim_w + HARDCOVER_WRAP_INCHES).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        full_height_in = (HARDCOVER_WRAP_INCHES + trim_h + HARDCOVER_WRAP_INCHES).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        full_width_pt = (full_width_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        full_height_pt = (full_height_in * POINTS_PER_INCH).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        spine_text_eligible = even_pages >= SPINE_TEXT_MIN_PAGE_THRESHOLD
        reason = None
        if not spine_text_eligible:
            reason = (
                f"Page count is {even_pages} (under {SPINE_TEXT_MIN_PAGE_THRESHOLD} pages). "
                f"Spine text requires at least 80 pages for physical case-laminate alignment."
            )

        wrap_pt = float(HARDCOVER_WRAP_INCHES * POINTS_PER_INCH)
        back_width_pt = float(trim_w * POINTS_PER_INCH)
        barcode_w_pt = 144.0
        barcode_h_pt = 86.4
        barcode_x = wrap_pt + back_width_pt - barcode_w_pt - 28.8  # Hinge clearance
        barcode_y = wrap_pt + 28.8

        return CoverCalculationResponse(
            format="hardcover",
            trim_size=trim_size,
            paper_type=norm_paper,
            interior_page_count=interior_page_count,
            even_page_count=even_pages,
            spine_coefficient=float(coeff),
            spine_width_inches=float(spine_width_in),
            spine_width_pt=float(spine_width_pt),
            full_cover_width_inches=float(full_width_in),
            full_cover_width_pt=float(full_width_pt),
            full_cover_height_inches=float(full_height_in),
            full_cover_height_pt=float(full_height_pt),
            bleed_inches=float(HARDCOVER_WRAP_INCHES),
            bleed_pt=float(HARDCOVER_WRAP_INCHES * POINTS_PER_INCH),
            safe_zone_margin_inches=float(HARDCOVER_SAFE_DISTANCE_INCHES),
            safe_zone_margin_pt=float(HARDCOVER_SAFE_DISTANCE_INCHES * POINTS_PER_INCH),
            spine_text_eligible=spine_text_eligible,
            spine_text_reason=reason,
            barcode_box={
                "x_pt": barcode_x,
                "y_pt": barcode_y,
                "width_pt": barcode_w_pt,
                "height_pt": barcode_h_pt,
            },
            provenance="Amazon KDP Hardcover Cover Specification (kdp.amazon.com/en_US/help/topic/G7S2GFJ6TP9A7F3H)",
            is_supported=False,
            restriction_reason="Hardcover automated standalone cover generation is restricted. Official Amazon KDP template geometry (from https://kdp.amazon.com/en_US/cover-templates) is required to guarantee manufacturing acceptance.",
            is_provisional=False,
            interior_document_id=None,
            is_kdp_compliant_page_count=even_pages >= 75,
            min_page_warning=None if even_pages >= 75 else f"KDP Hardcover requires minimum 75 pages. Current interior has {even_pages} pages.",
        )
