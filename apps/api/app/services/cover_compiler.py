import io
import os
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image as PILImage
import pypdf

from app.models.book import Book
from app.models.illustration import Illustration
from app.schemas.book_document import CoverGenerationRequest, CoverCalculationResponse
from app.services.cover_calculation import CoverCalculationService
from app.services.interior_compiler import ensure_embedded_fonts_registered
from app.core.storage import LocalAssetStorage
from app.core.security_fetcher import SecureAssetURLFetcher


class FullJacketCoverCompiler:
    """
    Compiler for single-page full-jacket Amazon KDP cover PDFs.
    Assembles back cover, spine, front cover, bleed, safe margins, and barcode clearance.
    """

    @classmethod
    def compile_cover(
        cls,
        book: Book,
        calc: CoverCalculationResponse,
        req: CoverGenerationRequest,
        front_ill: Optional[Illustration] = None,
        back_ill: Optional[Illustration] = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Render a full-jacket cover PDF with exact calculated dimensions.
        Returns: (pdf_bytes, metadata_dict)
        """
        w_pt = calc.full_cover_width_pt
        h_pt = calc.full_cover_height_pt
        bleed_pt = calc.bleed_pt
        spine_w_pt = calc.spine_width_pt

        # Physical section coordinates
        # Back cover width = (total_width - 2*bleed - spine) / 2
        back_w_pt = (w_pt - (2 * bleed_pt) - spine_w_pt) / 2.0
        front_w_pt = back_w_pt

        spine_x_left = bleed_pt + back_w_pt
        spine_x_right = spine_x_left + spine_w_pt
        front_x_left = spine_x_right

        # 0. Register and select embedded TrueType fonts
        fonts = ensure_embedded_fonts_registered()
        reg_font = fonts["sans"]["regular"]
        bold_font = fonts["sans"]["bold"]

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(w_pt, h_pt), initialFontName=reg_font)

        # ------------------------------------------------------------------
        # 1. Background Fill (Full Bleed)
        # ------------------------------------------------------------------
        try:
            bg_color = colors.HexColor(req.primary_color)
        except Exception:
            bg_color = colors.HexColor("#0f172a")

        c.setFillColor(bg_color)
        c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

        # ------------------------------------------------------------------
        # 2. Back Cover Artwork & Text
        # ------------------------------------------------------------------
        if back_ill and back_ill.storage_key:
            try:
                b_path = SecureAssetURLFetcher.validate_and_resolve_asset_path(back_ill.storage_key)
                with PILImage.open(b_path) as pimg:
                    pw, ph = pimg.size
                    scale = min((back_w_pt * 0.8) / pw, (h_pt * 0.4) / ph)
                    img_w = pw * scale
                    img_h = ph * scale
                    img_x = bleed_pt + (back_w_pt - img_w) / 2.0
                    img_y = h_pt * 0.50
                    c.drawImage(str(b_path), img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True)
            except Exception:
                pass

        # Back Cover Description
        desc_text = req.back_cover_description or book.topic or ""
        if desc_text:
            c.saveState()
            c.setFillColor(colors.white)
            c.setFont(reg_font, 9)
            # Wrap text inside back cover safe margins
            margin_x = bleed_pt + calc.safe_zone_margin_pt + 10.0
            max_text_w = back_w_pt - (calc.safe_zone_margin_pt * 2) - 20.0
            text_y = h_pt - calc.safe_zone_margin_pt - 40.0

            words = desc_text.split()
            line = ""
            for word in words:
                test_line = line + (" " if line else "") + word
                if c.stringWidth(test_line, reg_font, 9) < max_text_w:
                    line = test_line
                else:
                    c.drawString(margin_x, text_y, line)
                    text_y -= 13.0
                    line = word
                    if text_y < (calc.barcode_box["y_pt"] + calc.barcode_box["height_pt"] + 20.0):
                        break
            if line and text_y >= (calc.barcode_box["y_pt"] + calc.barcode_box["height_pt"] + 20.0):
                c.drawString(margin_x, text_y, line)
            c.restoreState()

        # Barcode Reserved Area
        bc = calc.barcode_box
        c.saveState()
        c.setFillColor(colors.white)
        c.setStrokeColor(colors.HexColor("#94a3b8"))
        c.setLineWidth(0.5)
        c.rect(bc["x_pt"], bc["y_pt"], bc["width_pt"], bc["height_pt"], fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#64748b"))
        c.setFont(reg_font, 7)
        c.drawCentredString(bc["x_pt"] + bc["width_pt"] / 2.0, bc["y_pt"] + bc["height_pt"] / 2.0 - 3.0, "BARCODE RESERVED AREA")
        c.restoreState()

        # ------------------------------------------------------------------
        # 3. Spine Area
        # ------------------------------------------------------------------
        # Distinct spine accent fill if desired
        c.saveState()
        c.setFillColor(colors.HexColor("#1e293b"))
        c.rect(spine_x_left, 0, spine_w_pt, h_pt, fill=1, stroke=0)
        c.restoreState()

        # Spine Text (Only if page count >= 80)
        if calc.spine_text_eligible and req.include_spine_text:
            spine_title = req.custom_front_title or book.title
            spine_author = req.custom_author_name or "AUTHOR"
            full_spine_string = f"{spine_title.upper()}    •    {spine_author.upper()}"

            c.saveState()
            c.setFillColor(colors.white)
            c.setFont(bold_font, 8)
            # Center of spine
            center_spine_x = spine_x_left + (spine_w_pt / 2.0)
            # Rotate 90 degrees clockwise (or -90 standard top-to-bottom)
            c.translate(center_spine_x + 3.0, h_pt * 0.50)
            c.rotate(-90)
            c.drawCentredString(0, 0, full_spine_string[:60])
            c.restoreState()

        # ------------------------------------------------------------------
        # 4. Front Cover Artwork & Typography
        # ------------------------------------------------------------------
        front_center_x = front_x_left + (front_w_pt / 2.0)

        # Front Artwork
        if front_ill and front_ill.storage_key:
            try:
                f_path = SecureAssetURLFetcher.validate_and_resolve_asset_path(front_ill.storage_key)
                with PILImage.open(f_path) as pimg:
                    pw, ph = pimg.size
                    max_art_w = front_w_pt - (calc.safe_zone_margin_pt * 2) - 20.0
                    max_art_h = h_pt * 0.40
                    scale = min(max_art_w / pw, max_art_h / ph)
                    art_w = pw * scale
                    art_h = ph * scale
                    art_x = front_center_x - (art_w / 2.0)
                    art_y = h_pt * 0.32
                    c.drawImage(str(f_path), art_x, art_y, width=art_w, height=art_h, preserveAspectRatio=True)
            except Exception:
                pass

        # Front Cover Title
        title_text = req.custom_front_title or book.title
        c.saveState()
        try:
            accent = colors.HexColor(req.accent_color)
        except Exception:
            accent = colors.HexColor("#f59e0b")

        c.setFillColor(accent)
        c.setFont(bold_font, 24)
        c.drawCentredString(front_center_x, h_pt - calc.safe_zone_margin_pt - 45.0, title_text.upper()[:40])

        # Subtitle
        sub_text = req.custom_front_subtitle or book.subtitle or ""
        if sub_text:
            c.setFillColor(colors.HexColor("#e2e8f0"))
            c.setFont(reg_font, 11)
            c.drawCentredString(front_center_x, h_pt - calc.safe_zone_margin_pt - 65.0, sub_text[:60])

        # Author Name
        author_text = req.custom_author_name or "AI MONEY COMPANION PRESS"
        c.setFillColor(colors.white)
        c.setFont(bold_font, 11)
        c.drawCentredString(front_center_x, bleed_pt + calc.safe_zone_margin_pt + 25.0, author_text.upper())
        c.restoreState()

        # ------------------------------------------------------------------
        # 5. Visual Guides (Only if render_guides is True)
        # ------------------------------------------------------------------
        if req.render_guides:
            c.saveState()
            c.setStrokeColor(colors.HexColor("#06b6d4"))
            c.setLineWidth(0.5)
            c.setDash(3, 3)

            # Bleed boundary
            c.rect(bleed_pt, bleed_pt, w_pt - 2 * bleed_pt, h_pt - 2 * bleed_pt, fill=0, stroke=1)
            # Spine fold lines
            c.line(spine_x_left, 0, spine_x_left, h_pt)
            c.line(spine_x_right, 0, spine_x_right, h_pt)
            c.restoreState()

        c.showPage()
        c.save()

        raw_bytes = buffer.getvalue()

        # Inspect resulting PDF
        reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
        page_count = len(reader.pages)
        first_page = reader.pages[0]
        actual_w = float(first_page.mediabox.width)
        actual_h = float(first_page.mediabox.height)

        metadata = {
            "renderer": "reportlab-cover-engine",
            "format": calc.format,
            "trim_size": calc.trim_size,
            "page_count": page_count,
            "width_pt": actual_w,
            "height_pt": actual_h,
            "spine_width_pt": spine_w_pt,
            "spine_text_eligible": calc.spine_text_eligible,
            "has_front_artwork": bool(front_ill and front_ill.storage_key),
            "has_back_artwork": bool(back_ill and back_ill.storage_key),
            "render_guides": req.render_guides,
        }

        return raw_bytes, metadata
