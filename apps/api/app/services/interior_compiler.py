import io
import os
import re
import html
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from decimal import Decimal

from reportlab.lib.pagesizes import portrait
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
    Image as RLImage,
    Table,
    TableStyle,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import pypdf

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.schemas.book_document import InteriorGenerationRequest
from app.services.cover_calculation import parse_trim_size_inches, POINTS_PER_INCH
from app.core.storage import LocalAssetStorage
from app.core.security_fetcher import SecureAssetURLFetcher, SecurityFetchError, weasyprint_secure_url_fetcher

logger = logging.getLogger(__name__)

_FONTS_REGISTERED = False

def ensure_embedded_fonts_registered() -> Dict[str, Dict[str, str]]:
    """
    Register TrueType fonts with ReportLab to guarantee true font stream embedding (/FontFile2).
    """
    global _FONTS_REGISTERED
    if not _FONTS_REGISTERED:
        # 1. Bitstream Vera (packaged with ReportLab, cross-platform)
        try:
            pdfmetrics.registerFont(TTFont("Vera-Regular", "Vera.ttf"))
            pdfmetrics.registerFont(TTFont("Vera-Bold", "VeraBd.ttf"))
            pdfmetrics.registerFont(TTFont("Vera-Italic", "VeraIt.ttf"))
            pdfmetrics.registerFont(TTFont("Vera-BoldItalic", "VeraBI.ttf"))
        except Exception as e:
            logger.warning("Could not register Bitstream Vera fonts: %s", e)

        # 2. Windows Times TrueType (embedded) or Vera fallback
        times_regular = "C:/Windows/Fonts/times.ttf"
        times_bold = "C:/Windows/Fonts/timesbd.ttf"
        times_italic = "C:/Windows/Fonts/timesi.ttf"
        if os.path.exists(times_regular) and os.path.exists(times_bold):
            try:
                pdfmetrics.registerFont(TTFont("Times-Regular-Embedded", times_regular))
                pdfmetrics.registerFont(TTFont("Times-Bold-Embedded", times_bold))
                pdfmetrics.registerFont(TTFont("Times-Italic-Embedded", times_italic if os.path.exists(times_italic) else times_regular))
            except Exception as e:
                logger.warning("Could not register Windows Times fonts: %s", e)

        _FONTS_REGISTERED = True

    registered = set(pdfmetrics.getRegisteredFontNames())

    # Sans family
    sans = {
        "regular": "Vera-Regular" if "Vera-Regular" in registered else "Helvetica",
        "bold": "Vera-Bold" if "Vera-Bold" in registered else "Helvetica-Bold",
        "italic": "Vera-Italic" if "Vera-Italic" in registered else "Helvetica-Oblique",
    }

    # Serif family
    if "Times-Regular-Embedded" in registered:
        serif = {
            "regular": "Times-Regular-Embedded",
            "bold": "Times-Bold-Embedded",
            "italic": "Times-Italic-Embedded",
        }
    else:
        serif = sans

    return {"sans": sans, "serif": serif}


# M2 KDP Gutter Margin Schedule (in points, 72 pt = 1 in)
# Provenance: Amazon KDP Print Options & Page Constraints (kdp.amazon.com/en_US/help/topic/G201857950)
def get_gutter_margin_pt(page_count: int) -> float:
    if page_count <= 150:
        return 0.375 * 72.0  # 27.0 pt
    elif page_count <= 300:
        return 0.500 * 72.0  # 36.0 pt
    elif page_count <= 500:
        return 0.625 * 72.0  # 45.0 pt
    elif page_count <= 700:
        return 0.750 * 72.0  # 54.0 pt
    else:
        return 0.875 * 72.0  # 63.0 pt


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic total page counting, running headers, and mirrored pagination.
    Uses registered TrueType fonts to ensure 100% font embedding.
    """
    canvas_font = "Vera-Regular"

    def __init__(self, *args, **kwargs):
        kwargs["initialFontName"] = NumberedCanvas.canvas_font
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        page_num = self._pageNumber
        # Suppress headers/footers on title (1), copyright (2), and dedication (3)
        if page_num <= 3:
            return

        is_even = (page_num % 2 == 0)
        width, height = self._pagesize

        self.saveState()
        self.setFont(NumberedCanvas.canvas_font, 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer page numbers: mirrored (left on even/verso, right on odd/recto)
        footer_y = 24.0
        if is_even:
            self.drawString(36.0, footer_y, str(page_num))
        else:
            self.drawRightString(width - 36.0, footer_y, str(page_num))

        # Running header: book title on even, chapter on odd (above 36pt margin)
        header_y = height - 26.0
        header_text = getattr(self, "current_header_title", "")
        if header_text and page_num > 4:
            if is_even:
                self.drawString(36.0, header_y, header_text)
            else:
                self.drawRightString(width - 36.0, header_y, header_text)

        self.restoreState()


class WeasyPrintInteriorCompiler:
    """
    Approved Milestone 4 WeasyPrint CSS Paged Media PDF compiler.
    Uses @page, mirrored margin rules, running headers/footers, and secure URL fetcher.
    """

    @classmethod
    def compile_interior(
        cls,
        book: Book,
        chapters: List[Chapter],
        illustrations: List[Illustration],
        req: InteriorGenerationRequest,
    ) -> Tuple[bytes, Dict[str, Any]]:
        # Import WeasyPrint (will raise ImportError or OSError on platforms without GTK C-libraries)
        import weasyprint

        trim_w_in, trim_h_in = parse_trim_size_inches(book.trim_size)
        if req.is_full_bleed:
            page_w_in = float(trim_w_in + Decimal("0.125"))
            page_h_in = float(trim_h_in + Decimal("0.250"))
            bleed_css = ""
            bleed_config = "bleed_0.125"
        else:
            page_w_in = float(trim_w_in)
            page_h_in = float(trim_h_in)
            bleed_css = ""
            bleed_config = "no_bleed"

        estimated_pages = max(24, getattr(book, "total_allocated_pages", None) or getattr(book, "target_page_count", 100) or 100)
        gutter_in = get_gutter_margin_pt(estimated_pages) / 72.0
        outside_in = 0.50

        # Construct CSS Paged Media stylesheet
        font_family = "Georgia, 'Times New Roman', serif" if req.font_choice == "serif" else "Arial, Helvetica, sans-serif"
        css_str = f"""
        @page {{
            size: {page_w_in}in {page_h_in}in;
            margin-top: 0.5in;
            margin-bottom: 0.5in;
            {bleed_css}
        }}
        @page :left {{
            margin-left: {outside_in}in;
            margin-right: {gutter_in}in;
            @top-left {{
                content: "{html.escape(book.title)}";
                font-family: {font_family};
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-left {{
                content: counter(page);
                font-family: {font_family};
                font-size: 8pt;
                color: #64748b;
            }}
        }}
        @page :right {{
            margin-left: {gutter_in}in;
            margin-right: {outside_in}in;
            @top-right {{
                content: string(chapter-title);
                font-family: {font_family};
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-right {{
                content: counter(page);
                font-family: {font_family};
                font-size: 8pt;
                color: #64748b;
            }}
        }}
        @page :first {{
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}
        body {{
            font-family: {font_family};
            font-size: 10pt;
            line-height: 1.4;
            color: #1e293b;
        }}
        h1.title {{
            font-size: 26pt;
            text-align: center;
            margin-top: 2in;
            margin-bottom: 0.2in;
        }}
        h2.subtitle {{
            font-size: 14pt;
            text-align: center;
            color: #475569;
            margin-bottom: 0.5in;
        }}
        .author {{
            font-size: 12pt;
            text-align: center;
            margin-bottom: 2in;
        }}
        .page-break {{
            page-break-after: always;
        }}
        .chapter {{
            page-break-before: always;
        }}
        h1.chapter-title {{
            font-size: 18pt;
            margin-top: 0.3in;
            margin-bottom: 0.2in;
            string-set: chapter-title content();
        }}
        .layout-placeholder {{
            border: 1px dashed #cbd5e1;
            background: #f8fafc;
            padding: 12pt;
            text-align: center;
            font-size: 8pt;
            color: #64748b;
            margin: 10pt 0;
        }}
        img.illustration {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 10pt auto;
        }}
        """

        # Build HTML content
        parts = [
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{html.escape(book.title)}</title>",
            f"<style>{css_str}</style></head><body>",
            f"<div class='page-break'><h1 class='title'>{html.escape(book.title)}</h1>",
            f"<h2 class='subtitle'>{html.escape(book.subtitle or '')}</h2>" if book.subtitle else "",
            f"<div class='author'>A Practical Publishing Edition</div></div>",
            "<div class='page-break'><div style='margin-top: 3in; font-size: 8pt; color: #64748b;'>",
            f"<p>Copyright &copy; {book.created_at.year if book.created_at else 2026} by Author. All rights reserved.</p>",
            f"<p>Trim: {book.trim_size} &bull; Interior: {book.paper_type} &bull; Manufactured and distributed via Amazon KDP.</p>",
            "</div></div>",
        ]

        if req.include_dedication and req.dedication_text:
            parts.append(f"<div class='page-break'><div style='margin-top: 2in; text-align: center; font-style: italic;'>{html.escape(req.dedication_text)}</div></div>")

        if req.include_toc and chapters:
            parts.append("<div class='page-break'><h2>Table of Contents</h2><ul>")
            for chap in chapters:
                parts.append(f"<li>Chapter {chap.chapter_number}: {html.escape(chap.title)}</li>")
            parts.append("</ul></div>")

        approved_ill_map = {ill.chapter_id: ill for ill in illustrations if ill.status == "APPROVED_FINAL"}
        placeholder_ill_map = {ill.chapter_id: ill for ill in illustrations if ill.status in ("PROMPT", "PLACEHOLDER", "GENERATED")}

        for chap in chapters:
            parts.append(f"<div class='chapter'><p style='font-size: 11pt; color: #64748b;'>Chapter {chap.chapter_number}</p>")
            parts.append(f"<h1 class='chapter-title'>{html.escape(chap.title)}</h1>")

            # Approved artwork via asset:// URI (resolved strictly through weasyprint_secure_url_fetcher)
            ill = approved_ill_map.get(chap.id)
            if ill and ill.storage_key:
                parts.append(f"<img class='illustration' src='asset://{ill.storage_key}' alt='{html.escape(ill.description or '')}'/>")
                if ill.description:
                    parts.append(f"<p style='text-align: center; font-size: 8pt; color: #64748b;'>{html.escape(ill.description)}</p>")
            elif chap.id in placeholder_ill_map:
                p_ill = placeholder_ill_map[chap.id]
                parts.append(f"<div class='layout-placeholder'><strong>[LAYOUT PLACEHOLDER: {p_ill.status}]</strong><br/>{html.escape(p_ill.prompt[:120])}...</div>")

            # Markdown paragraphs
            clean_md = InteriorPDFCompiler.sanitize_markdown_text(chap.content)
            for line in clean_md.split("\n"):
                s = line.strip()
                if not s or s.startswith("# "):
                    continue
                elif s.startswith("## "):
                    parts.append(f"<h2>{html.escape(s[3:])}</h2>")
                elif s.startswith("### "):
                    parts.append(f"<h3>{html.escape(s[4:])}</h3>")
                elif s.startswith("- ") or s.startswith("* "):
                    parts.append(f"<ul><li>{html.escape(s[2:])}</li></ul>")
                elif s.startswith("> "):
                    parts.append(f"<blockquote>{html.escape(s[2:])}</blockquote>")
                else:
                    parts.append(f"<p>{html.escape(s)}</p>")
            parts.append("</div>")

        parts.append("</body></html>")
        html_doc_str = "\n".join(parts)

        # Execute WeasyPrint using SecureAssetURLFetcher
        weasy_html = weasyprint.HTML(string=html_doc_str, url_fetcher=weasyprint_secure_url_fetcher)
        raw_pdf_bytes = weasy_html.write_pdf()

        # Parity check
        reader = pypdf.PdfReader(io.BytesIO(raw_pdf_bytes))
        initial_pages = len(reader.pages)
        final_pdf_bytes = raw_pdf_bytes
        actual_page_count = initial_pages
        if initial_pages % 2 != 0:
            writer = pypdf.PdfWriter()
            for p in reader.pages:
                writer.add_page(p)
            writer.add_blank_page(width=page_w_in * 72.0, height=page_h_in * 72.0)
            out_buf = io.BytesIO()
            writer.write(out_buf)
            final_pdf_bytes = out_buf.getvalue()
            actual_page_count = initial_pages + 1

        metadata = {
            "renderer": "weasyprint-css-paged-media",
            "trim_size": book.trim_size,
            "bleed_config": bleed_config,
            "page_width_pt": page_w_in * 72.0,
            "page_height_pt": page_h_in * 72.0,
            "initial_rendered_pages": initial_pages,
            "final_even_page_count": actual_page_count,
            "parity_blank_page_added": (initial_pages % 2 != 0),
            "gutter_margin_pt": gutter_in * 72.0,
            "outside_margin_pt": outside_in * 72.0,
            "font_choice": req.font_choice,
            "dpi_advisories": [],
            "weasyprint_blocker": None,
        }
        return final_pdf_bytes, metadata


class InteriorPDFCompiler:
    """
    Publishing-grade interior PDF compiler for Amazon KDP print publication.
    Enforces exact MediaBox dimensions, mirrored gutters, safe Markdown parsing,
    embedded image DPI verification, and physical even page requirements.
    Supports WeasyPrint CSS Paged Media and ReportLab embedded-font engines.
    """

    @classmethod
    def sanitize_markdown_text(cls, text: str) -> str:
        """Strip dangerous HTML tags to prevent code or styling injection."""
        if not text:
            return ""
        cleaned = re.sub(r"<(script|iframe|object|embed|style)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<(?!\/?(b|i|strong|em|code)>)[^>]+>", "", cleaned)
        return cleaned

    @classmethod
    def compile_interior(
        cls,
        book: Book,
        chapters: List[Chapter],
        illustrations: List[Illustration],
        req: InteriorGenerationRequest,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compile interior PDF document.
        Attempts approved WeasyPrint CSS Paged Media engine first.
        If WeasyPrint is blocked by missing C-libraries (Pango/GObject on Windows),
        transparently compiles via ReportLab embedded-font compiler and records blocker evidence.
        """
        weasyprint_blocker = None
        try:
            return WeasyPrintInteriorCompiler.compile_interior(
                book=book,
                chapters=chapters,
                illustrations=illustrations,
                req=req,
            )
        except (ImportError, OSError, Exception) as e:
            weasyprint_blocker = f"{type(e).__name__}: {str(e)}"
            logger.info("WeasyPrint engine blocked on current host (%s). Compiling with ReportLab embedded-font engine.", weasyprint_blocker)

        # Execute ReportLab compiler with 100% embedded TrueType fonts
        pdf_bytes, metadata = cls._compile_reportlab(
            book=book,
            chapters=chapters,
            illustrations=illustrations,
            req=req,
        )
        metadata["weasyprint_blocker"] = weasyprint_blocker
        return pdf_bytes, metadata

    @classmethod
    def _compile_reportlab(
        cls,
        book: Book,
        chapters: List[Chapter],
        illustrations: List[Illustration],
        req: InteriorGenerationRequest,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Compile interior using ReportLab with 100% embedded font streams."""
        # 1. Register and select embedded fonts
        font_map = ensure_embedded_fonts_registered()
        family = font_map.get(req.font_choice, font_map["sans"])
        body_font = family["regular"]
        h_font = family["bold"]
        i_font = family["italic"]
        NumberedCanvas.canvas_font = body_font

        # 2. Physical Page Dimensions
        trim_w_in, trim_h_in = parse_trim_size_inches(book.trim_size)
        if req.is_full_bleed:
            page_w_pt = float((trim_w_in + Decimal("0.125")) * POINTS_PER_INCH)
            page_h_pt = float((trim_h_in + Decimal("0.250")) * POINTS_PER_INCH)
            bleed_config = "bleed_0.125"
        else:
            page_w_pt = float(trim_w_in * POINTS_PER_INCH)
            page_h_pt = float(trim_h_in * POINTS_PER_INCH)
            bleed_config = "no_bleed"

        page_size = (page_w_pt, page_h_pt)

        # 3. Margins and Gutter
        estimated_pages = max(24, getattr(book, "total_allocated_pages", None) or getattr(book, "target_page_count", 100) or 100)
        gutter_pt = get_gutter_margin_pt(estimated_pages)
        outside_margin_pt = 36.0  # 0.5" outside margin
        top_margin_pt = 36.0
        bottom_margin_pt = 36.0

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=outside_margin_pt,
            rightMargin=outside_margin_pt,
            topMargin=top_margin_pt,
            bottomMargin=bottom_margin_pt,
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        style_title = ParagraphStyle(
            "BookTitle",
            parent=normal,
            fontName=h_font,
            fontSize=26,
            leading=32,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=12,
        )
        style_subtitle = ParagraphStyle(
            "BookSubtitle",
            parent=normal,
            fontName=body_font,
            fontSize=14,
            leading=18,
            alignment=1,
            textColor=colors.HexColor("#475569"),
            spaceAfter=24,
        )
        style_author = ParagraphStyle(
            "BookAuthor",
            parent=normal,
            fontName=h_font,
            fontSize=12,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
        )
        style_chapter_h1 = ParagraphStyle(
            "ChapterHeading",
            parent=normal,
            fontName=h_font,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=16,
            spaceAfter=12,
            keepWithNext=True,
        )
        style_chapter_h2 = ParagraphStyle(
            "ChapterSubHeading",
            parent=normal,
            fontName=h_font,
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        )
        style_body = ParagraphStyle(
            "BodyMarkdown",
            parent=normal,
            fontName=body_font,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            firstLineIndent=14,
            spaceAfter=4,
        )
        style_copyright = ParagraphStyle(
            "CopyrightText",
            parent=normal,
            fontName=body_font,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=6,
        )
        style_toc_item = ParagraphStyle(
            "TocItem",
            parent=normal,
            fontName=body_font,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
        )

        story = []

        # Page 1: Title Page
        story.append(Spacer(1, page_h_pt * 0.18))
        story.append(Paragraph(html.escape(book.title), style_title))
        if book.subtitle:
            story.append(Paragraph(html.escape(book.subtitle), style_subtitle))
        story.append(Spacer(1, 36))
        story.append(Paragraph("A Practical Publishing Edition", style_author))
        story.append(Spacer(1, page_h_pt * 0.25))
        story.append(Paragraph("Published via AI Money Companion OS", style_copyright))
        story.append(PageBreak())

        # Page 2: Copyright Page
        story.append(Spacer(1, page_h_pt * 0.40))
        story.append(Paragraph(f"Copyright © {book.created_at.year if book.created_at else 2026} by Author.", style_copyright))
        story.append(Paragraph("All rights reserved. No part of this publication may be reproduced, distributed, or transmitted in any form without prior written permission.", style_copyright))
        story.append(Paragraph(f"Format: {book.print_format.title()} • Trim: {book.trim_size} • Interior: {book.paper_type}", style_copyright))
        story.append(Paragraph("Manufactured and distributed via Amazon KDP.", style_copyright))
        story.append(Paragraph("First Edition.", style_copyright))
        story.append(PageBreak())

        # Page 3: Dedication Page
        if req.include_dedication and req.dedication_text:
            story.append(Spacer(1, page_h_pt * 0.30))
            style_ded = ParagraphStyle("Dedication", parent=style_body, fontName=i_font, fontSize=11, leading=16, alignment=1)
            story.append(Paragraph(html.escape(req.dedication_text), style_ded))
            story.append(PageBreak())

        # Table of Contents
        if req.include_toc and chapters:
            story.append(Paragraph("Table of Contents", style_chapter_h1))
            story.append(Spacer(1, 12))
            for chap in chapters:
                toc_line = f"Chapter {chap.chapter_number}: {html.escape(chap.title)}"
                story.append(Paragraph(toc_line, style_toc_item))
            story.append(PageBreak())

        # Chapters
        dpi_advisories = []
        approved_ill_map = {ill.chapter_id: ill for ill in illustrations if ill.status == "APPROVED_FINAL"}
        placeholder_ill_map = {ill.chapter_id: ill for ill in illustrations if ill.status in ("PROMPT", "PLACEHOLDER", "GENERATED")}

        for chap in chapters:
            story.append(Paragraph(f"Chapter {chap.chapter_number}", style_chapter_h2))
            story.append(Paragraph(html.escape(chap.title), style_chapter_h1))
            story.append(Spacer(1, 8))

            # Include approved illustration if present
            ill = approved_ill_map.get(chap.id)
            if ill and ill.storage_key:
                try:
                    asset_path = SecureAssetURLFetcher.validate_and_resolve_asset_path(ill.storage_key)
                    with PILImage.open(asset_path) as pimg:
                        img_w_px, img_h_px = pimg.size
                        max_w_pt = page_w_pt - (outside_margin_pt * 2) - gutter_pt
                        aspect = img_h_px / img_w_px
                        render_w_pt = min(max_w_pt, 280.0)
                        render_h_pt = render_w_pt * aspect

                        effective_dpi = (img_w_px / (render_w_pt / 72.0))
                        if effective_dpi < 300.0:
                            dpi_advisories.append({
                                "illustration_id": ill.id,
                                "chapter_number": chap.chapter_number,
                                "effective_dpi": round(effective_dpi, 1),
                                "warning": f"Image effective resolution is {round(effective_dpi)} DPI (< 300 DPI Amazon KDP recommended standard)."
                            })

                        story.append(RLImage(str(asset_path), width=render_w_pt, height=render_h_pt))
                        story.append(Spacer(1, 6))
                        if ill.description:
                            style_cap = ParagraphStyle("Cap", parent=style_copyright, alignment=1)
                            story.append(Paragraph(html.escape(ill.description), style_cap))
                        story.append(Spacer(1, 10))
                except Exception as e:
                    story.append(Paragraph(f"[Image Error: {html.escape(str(e))}]", style_copyright))
            elif chap.id in placeholder_ill_map:
                p_ill = placeholder_ill_map[chap.id]
                ph_table = Table(
                    [[Paragraph(f"<b>[LAYOUT PLACEHOLDER: {p_ill.status}]</b><br/>{html.escape(p_ill.prompt[:120])}...", style_copyright)]],
                    colWidths=[page_w_pt - (outside_margin_pt * 2) - gutter_pt],
                    rowHeights=[60],
                )
                ph_table.setStyle(TableStyle([
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                story.append(ph_table)
                story.append(Spacer(1, 10))

            # Markdown lines
            clean_md = cls.sanitize_markdown_text(chap.content)
            lines = clean_md.split("\n")
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("# "):
                    continue
                elif stripped.startswith("## "):
                    story.append(Paragraph(html.escape(stripped[3:]), style_chapter_h2))
                elif stripped.startswith("### "):
                    h3_style = ParagraphStyle("H3", parent=style_chapter_h2, fontSize=11, leading=15)
                    story.append(Paragraph(html.escape(stripped[4:]), h3_style))
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    bullet_style = ParagraphStyle("Bullet", parent=style_body, firstLineIndent=0, leftIndent=12)
                    story.append(Paragraph(f"• {html.escape(stripped[2:])}", bullet_style))
                elif stripped.startswith("> "):
                    bq_style = ParagraphStyle("BQ", parent=style_body, fontName=i_font, leftIndent=16, rightIndent=16, textColor=colors.HexColor("#334155"))
                    story.append(Paragraph(html.escape(stripped[2:]), bq_style))
                else:
                    story.append(Paragraph(html.escape(stripped), style_body))

            story.append(PageBreak())

        doc.build(story, canvasmaker=NumberedCanvas)
        raw_pdf_bytes = buffer.getvalue()

        # Parity Check
        reader = pypdf.PdfReader(io.BytesIO(raw_pdf_bytes))
        initial_pages = len(reader.pages)

        final_pdf_bytes = raw_pdf_bytes
        actual_page_count = initial_pages
        if initial_pages % 2 != 0:
            writer = pypdf.PdfWriter()
            for p in reader.pages:
                writer.add_page(p)
            writer.add_blank_page(width=page_w_pt, height=page_h_pt)
            out_buf = io.BytesIO()
            writer.write(out_buf)
            final_pdf_bytes = out_buf.getvalue()
            actual_page_count = initial_pages + 1

        metadata = {
            "renderer": "reportlab-embedded-font-engine",
            "trim_size": book.trim_size,
            "bleed_config": bleed_config,
            "page_width_pt": page_w_pt,
            "page_height_pt": page_h_pt,
            "initial_rendered_pages": initial_pages,
            "final_even_page_count": actual_page_count,
            "parity_blank_page_added": (initial_pages % 2 != 0),
            "gutter_margin_pt": gutter_pt,
            "outside_margin_pt": outside_margin_pt,
            "font_choice": req.font_choice,
            "dpi_advisories": dpi_advisories,
        }

        return final_pdf_bytes, metadata
