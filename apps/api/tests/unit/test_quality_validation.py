import io
import pytest
import pypdf
from app.services.quality_validation import (
    QualityValidationService,
    count_syllables_english,
)


def test_syllable_counter():
    assert count_syllables_english("cash") == 1
    assert count_syllables_english("money") == 2
    assert count_syllables_english("allocation") == 4
    assert count_syllables_english("system") == 2


def test_readability_analysis_english():
    sample = (
        "The automated cash flow architecture enables authors to manage personal finances systematically. "
        "Every dollar earned is routed into predetermined reserve buckets. "
        "This methodology guarantees long term liquidity and operational peace of mind."
    )
    result = QualityValidationService.analyze_readability(sample, language="en")
    assert result["is_supported"] is True
    assert result["flesch_reading_ease"] is not None
    assert result["flesch_kincaid_grade"] is not None
    assert result["word_count"] > 20


def test_readability_analysis_unsupported_language():
    result = QualityValidationService.analyze_readability("Bonjour le monde.", language="fr")
    assert result["is_supported"] is False
    assert result["flesch_reading_ease"] is None
    assert "exclusively for English" in result["advisory"]


def test_amazon_policy_phrase_detection():
    findings = QualityValidationService.audit_manuscript_content(
        book_title="Test Book",
        chapters=[
            {"chapter_number": 1, "title": "Intro", "content": "Welcome to this guide."},
        ],
        cover_texts=["The #1 Amazon Best Seller Guide", "Free Bonus CD included!"],
    )
    rule_ids = [f["rule_id"] for f in findings]
    assert "KDP-POL-001" in rule_ids  # Bestseller prohibited on cover
    assert "KDP-POL-003" in rule_ids  # Bonus CD prohibited


def test_empty_chapter_warning():
    findings = QualityValidationService.audit_manuscript_content(
        book_title="Test Book",
        chapters=[
            {"chapter_number": 1, "title": "Empty Chapter", "content": ""},
        ],
    )
    rule_ids = [f["rule_id"] for f in findings]
    assert "CNT-EMP-001" in rule_ids


def test_pdf_structure_validation_valid():
    # Create simple valid PDF in memory
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=432.0, height=648.0)
    writer.write(buf)
    raw = buf.getvalue()

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=raw,
        document_type="COVER",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=1,
    )
    assert res["is_valid"] is True
    assert res["page_count"] == 1


def test_pdf_structure_encrypted_rejected():
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=432.0, height=648.0)
    writer.encrypt("secret_password")
    writer.write(buf)
    encrypted_bytes = buf.getvalue()

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=encrypted_bytes,
        document_type="INTERIOR",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=1,
    )
    assert res["is_valid"] is False
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "PDF-ENC-001" in rule_ids


def test_pdf_structure_dimension_mismatch_blocking():
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=500.0, height=700.0)
    writer.write(buf)
    raw = buf.getvalue()

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=raw,
        document_type="COVER",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=1,
    )
    assert res["is_valid"] is False
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "PDF-DIM-001" in rule_ids


def test_repetitive_passages_detection():
    # 4 paragraphs starting with same 3-word n-gram
    c1 = "In this chapter we look at cash.\n\nIn this chapter we analyze savings.\n\nIn this chapter we track debt.\n\nIn this chapter we plan taxes."
    findings = QualityValidationService.audit_manuscript_content(
        book_title="Book",
        chapters=[{"chapter_number": 1, "title": "C1", "content": c1}],
    )
    rule_ids = [f["rule_id"] for f in findings]
    assert "TXT-REP-001" in rule_ids


def test_pdf_font_embedding_negative_unembedded_base14():
    """Unembedded Base-14 font reference without /FontFile stream must be detected and flagged."""
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(432.0, 648.0))
    c.setFont("Helvetica", 12)
    c.drawString(100, 500, "Unembedded font test string.")
    c.save()

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=buf.getvalue(),
        document_type="INTERIOR",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=1,
    )

    assert res["all_fonts_embedded"] is False
    assert "/Helvetica" in res["unembedded_fonts"]
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "PDF-FNT-001" in rule_ids


def test_pdf_font_embedding_positive_truetype_stream():
    """PDF with real TrueType /FontFile2 stream must be verified as fully embedded."""
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont("Vera-Regular", "Vera.ttf"))

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(432.0, 648.0), initialFontName="Vera-Regular")
    c.setFont("Vera-Regular", 12)
    c.drawString(100, 500, "TrueType embedded font test string.")
    c.save()

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=buf.getvalue(),
        document_type="INTERIOR",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=1,
    )

    assert res["all_fonts_embedded"] is True
    assert len(res["unembedded_fonts"]) == 0
    assert any("BitstreamVeraSans" in f for f in res["embedded_fonts"])
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "PDF-FNT-001" not in rule_ids


def test_interior_below_24_pages_rejected():
    """6-page interior PDF must never be accepted as valid KDP paperback interior."""
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    for _ in range(6):
        writer.add_blank_page(width=432.0, height=648.0)
    writer.write(buf)

    res = QualityValidationService.validate_pdf_structure(
        pdf_bytes=buf.getvalue(),
        document_type="INTERIOR",
        expected_width_pt=432.0,
        expected_height_pt=648.0,
        min_pages=24,
    )

    assert res["is_valid"] is False
    rule_ids = [f["rule_id"] for f in res["findings"]]
    assert "PDF-PAG-002" in rule_ids
    pag_finding = next(f for f in res["findings"] if f["rule_id"] == "PDF-PAG-002")
    assert "below the minimum of 24 pages" in pag_finding["explanation"]
