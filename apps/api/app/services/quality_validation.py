import re
import io
from typing import List, Dict, Any, Optional
import pypdf

# Configurable Amazon KDP Policy Rule Registry
# Provenance: Amazon KDP Metadata Guidelines (kdp.amazon.com/en_US/help/topic/G201097560)
# and Amazon KDP Content Guidelines (kdp.amazon.com/en_US/help/topic/G200672390)
POLICY_RULES = [
    {
        "id": "KDP-POL-001",
        "pattern": r"\b(amazon\s+)?best[\s-]?seller\b",
        "category": "AMAZON_POLICY",
        "severity": "BLOCKING",
        "context": "cover",
        "explanation": "Amazon KDP strictly prohibits references to bestseller status, sales ranks, or awards on book covers.",
        "correction": "Remove references to 'Bestseller' or sales rankings from cover artwork and titles.",
        "provenance": "Amazon KDP Metadata Guidelines - Prohibited Content",
    },
    {
        "id": "KDP-POL-002",
        "pattern": r"\b(100%\s+)?free\b",
        "category": "AMAZON_POLICY",
        "severity": "BLOCKING",
        "context": "cover",
        "explanation": "Pricing references such as 'Free' or 'Discounted' are prohibited on KDP print covers and titles.",
        "correction": "Remove pricing or promotional discount claims.",
        "provenance": "Amazon KDP Metadata Guidelines - Prohibited Content",
    },
    {
        "id": "KDP-POL-003",
        "pattern": r"\b(bonus\s+(cd|dvd|disc|audiobook))\b",
        "category": "AMAZON_POLICY",
        "severity": "BLOCKING",
        "context": "both",
        "explanation": "Claims of included physical bonus media (CDs, DVDs) cannot be fulfilled via KDP print on demand.",
        "correction": "Replace physical media claims with links to online web resources.",
        "provenance": "Amazon KDP Physical Manufacturing Limitations",
    },
    {
        "id": "KDP-POL-004",
        "pattern": r"\bkindle\s+edition\b",
        "category": "AMAZON_POLICY",
        "severity": "WARNING",
        "context": "both",
        "explanation": "Reference to 'Kindle Edition' found on print manuscript or cover.",
        "correction": "Ensure print editions refer to Paperback or Hardcover, not Kindle Edition.",
        "provenance": "Amazon KDP Edition Formatting Consistency",
    },
    {
        "id": "KDP-POL-005",
        "pattern": r"\b(guaranteed\s+results|100%\s+guaranteed|get\s+rich\s+guaranteed)\b",
        "category": "AMAZON_POLICY",
        "severity": "WARNING",
        "context": "both",
        "explanation": "Promissory financial or health guarantees are scrutinized by Amazon KDP review teams.",
        "correction": "Softens claims to reflect practical educational principles without promising guaranteed outcomes.",
        "provenance": "Amazon KDP Quality Assurance Advisories",
    },
]


def count_syllables_english(word: str) -> int:
    """Heuristic English syllable counter based on vowel groups and morphology."""
    w = word.lower().strip()
    if len(w) <= 3:
        return 1
    # Remove trailing 'e' if not 'le'
    if w.endswith("e") and not w.endswith("le"):
        w = w[:-1]
    # Count consecutive vowels
    vowels = "aeiouy"
    count = len(re.findall(r"[aeiouy]+", w))
    return max(1, count)


class QualityValidationService:
    """
    Automated pre-flight quality and policy validation service.
    Analyzes manuscript text readability, detects repetition, checks Amazon claims,
    and inspects generated PDF files for physical integrity.
    """

    @classmethod
    def analyze_readability(cls, text: str, language: str = "en") -> Dict[str, Any]:
        """
        Calculate Flesch Reading Ease and Flesch-Kincaid Grade Level for English.
        Returns explicit limitation note if non-English.
        """
        if not language.lower().startswith("en"):
            return {
                "is_supported": False,
                "language": language,
                "flesch_reading_ease": None,
                "flesch_kincaid_grade": None,
                "advisory": f"Readability formulas are calibrated exclusively for English. Metrics not applicable for language '{language}'.",
            }

        words = re.findall(r"\b[a-zA-Z]+\b", text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

        word_count = len(words)
        sentence_count = max(1, len(sentences))

        if word_count < 10:
            return {
                "is_supported": True,
                "language": "en",
                "word_count": word_count,
                "sentence_count": sentence_count,
                "flesch_reading_ease": None,
                "flesch_kincaid_grade": None,
                "advisory": "Text sample too brief (< 10 words) for meaningful statistical readability scoring.",
            }

        total_syllables = sum(count_syllables_english(w) for w in words)
        asl = word_count / sentence_count  # Average sentence length
        asw = total_syllables / word_count  # Average syllables per word

        # Standard Flesch Reading Ease formula
        flesch_ease = round(206.835 - (1.015 * asl) - (84.6 * asw), 1)
        # Flesch-Kincaid Grade Level formula
        fk_grade = round((0.39 * asl) + (11.8 * asw) - 15.59, 1)

        # Interpret Reading Ease
        if flesch_ease >= 80:
            interpretation = "Easy (Conversational & Highly Accessible)"
        elif flesch_ease >= 60:
            interpretation = "Standard (Plain English & Practical Non-Fiction)"
        elif flesch_ease >= 50:
            interpretation = "Fairly Difficult (Technical or Advanced Concepts)"
        else:
            interpretation = "Difficult (Academic or Dense Sentence Structures)"

        return {
            "is_supported": True,
            "language": "en",
            "word_count": word_count,
            "sentence_count": sentence_count,
            "total_syllables": total_syllables,
            "flesch_reading_ease": max(0.0, min(100.0, flesch_ease)),
            "flesch_kincaid_grade": max(1.0, fk_grade),
            "reading_ease_band": interpretation,
        }

    @classmethod
    def audit_manuscript_content(
        cls,
        book_title: str,
        chapters: List[Dict[str, Any]],
        cover_texts: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Scan all chapters and cover text for Amazon policy violations,
        severe repetition, very short sections, and sentence anomalies.
        """
        findings = []

        # 1. Amazon Policy Checks on Cover Texts
        all_cover_text = " ".join(cover_texts or [])
        for rule in POLICY_RULES:
            if rule["context"] in ("cover", "both"):
                match = re.search(rule["pattern"], all_cover_text, re.IGNORECASE)
                if match:
                    findings.append({
                        "rule_id": rule["id"],
                        "category": rule["category"],
                        "severity": rule["severity"],
                        "location": "Cover Typography / Description",
                        "matched_term": match.group(0),
                        "explanation": rule["explanation"],
                        "suggested_correction": rule["correction"],
                        "provenance": rule["provenance"],
                    })

        # 2. Content Quality & Chapter Audits
        seen_starters: Dict[str, int] = {}
        for chap in chapters:
            c_num = chap.get("chapter_number", 0)
            c_title = chap.get("title", "")
            c_content = chap.get("content", "")
            location = f"Chapter {c_num}: {c_title}"

            # Check for empty or very short chapter
            words = re.findall(r"\b\w+\b", c_content)
            if len(words) == 0:
                findings.append({
                    "rule_id": "CNT-EMP-001",
                    "category": "CONTENT_QUALITY",
                    "severity": "WARNING",
                    "location": location,
                    "explanation": "Chapter contains zero manuscript words.",
                    "suggested_correction": "Draft or write content for this chapter before publishing.",
                    "provenance": "KDP Publication Completeness Standard",
                })
            elif len(words) < 50:
                findings.append({
                    "rule_id": "CNT-SHT-002",
                    "category": "CONTENT_QUALITY",
                    "severity": "ADVISORY",
                    "location": location,
                    "explanation": f"Chapter is unusually short ({len(words)} words).",
                    "suggested_correction": "Consider expanding section with actionable examples.",
                    "provenance": "Editorial Quality Advisory",
                })

            # Check Amazon Policy in chapter body
            for rule in POLICY_RULES:
                if rule["context"] in ("both",):
                    m = re.search(rule["pattern"], c_content, re.IGNORECASE)
                    if m:
                        findings.append({
                            "rule_id": rule["id"],
                            "category": rule["category"],
                            "severity": rule["severity"],
                            "location": location,
                            "matched_term": m.group(0),
                            "explanation": rule["explanation"],
                            "suggested_correction": rule["correction"],
                            "provenance": rule["provenance"],
                        })

            # Check for repetitive paragraph openings (3-word n-gram)
            paras = [p.strip() for p in c_content.split("\n\n") if p.strip()]
            for p in paras:
                p_words = p.split()[:3]
                if len(p_words) == 3:
                    starter = " ".join(p_words).lower()
                    seen_starters[starter] = seen_starters.get(starter, 0) + 1

        # Flag excessive identical paragraph openings
        for starter, count in seen_starters.items():
            if count >= 4:
                findings.append({
                    "rule_id": "TXT-REP-001",
                    "category": "CONTENT_QUALITY",
                    "severity": "ADVISORY",
                    "location": "Manuscript Body",
                    "explanation": f"Repeated paragraph opening '{starter}...' detected {count} times across chapters.",
                    "suggested_correction": "Vary sentence openings to improve prose cadence and rhythm.",
                    "provenance": "Prose Styling & Flow Heuristic",
                })

        return findings

    @classmethod
    def validate_pdf_structure(
        cls,
        pdf_bytes: bytes,
        document_type: str,
        expected_width_pt: float,
        expected_height_pt: float,
        min_pages: int = 1,
    ) -> Dict[str, Any]:
        """
        Inspect physical PDF using pypdf:
        Verifies MediaBox dimensions, single-page geometry, encryption, page counts, and file size limits.
        """
        findings = []
        file_size_bytes = len(pdf_bytes)

        # 1. KDP Max File Size Check (650 MB blocking ceiling)
        if file_size_bytes > 650 * 1024 * 1024:
            findings.append({
                "rule_id": "PDF-SIZ-001",
                "category": "PDF_STRUCTURE",
                "severity": "BLOCKING",
                "explanation": f"File size ({round(file_size_bytes / (1024*1024), 1)} MB) exceeds Amazon KDP maximum ceiling of 650 MB.",
                "provenance": "Amazon KDP File Creation Guide",
            })
        elif document_type == "COVER" and file_size_bytes > 40 * 1024 * 1024:
            findings.append({
                "rule_id": "PDF-SIZ-002",
                "category": "PDF_STRUCTURE",
                "severity": "ADVISORY",
                "explanation": f"Cover file size ({round(file_size_bytes / (1024*1024), 1)} MB) exceeds 40 MB optimization recommendation.",
                "provenance": "Amazon KDP Cover Optimization Guidelines",
            })

        # 2. PDF Parse and Integrity
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"Failed to parse PDF document: {str(e)}",
                "findings": [{
                    "rule_id": "PDF-COR-001",
                    "category": "PDF_STRUCTURE",
                    "severity": "BLOCKING",
                    "explanation": f"Corrupt or unreadable PDF: {str(e)}",
                    "provenance": "PDF Standard ISO 32000-1",
                }],
            }

        # 3. Encryption Check
        if reader.is_encrypted:
            return {
                "is_valid": False,
                "page_count": 0,
                "file_size_bytes": file_size_bytes,
                "findings": [{
                    "rule_id": "PDF-ENC-001",
                    "category": "PDF_STRUCTURE",
                    "severity": "BLOCKING",
                    "explanation": "Amazon KDP strictly rejects password-protected or encrypted PDF files.",
                    "provenance": "Amazon KDP PDF Specifications",
                }],
            }

        actual_page_count = len(reader.pages)

        # 4. Cover Single-Page Verification
        if document_type == "COVER":
            if actual_page_count != 1:
                findings.append({
                    "rule_id": "PDF-PAG-001",
                    "category": "PDF_STRUCTURE",
                    "severity": "BLOCKING",
                    "explanation": f"Cover PDF must contain exactly 1 single full-jacket page. Found {actual_page_count} pages.",
                    "provenance": "Amazon KDP Cover Specifications",
                })
        else:
            # Interior Page Count Constraints (min 24 pages for standard KDP print)
            if actual_page_count < min_pages:
                findings.append({
                    "rule_id": "PDF-PAG-002",
                    "category": "PDF_STRUCTURE",
                    "severity": "BLOCKING",
                    "explanation": f"Interior PDF has {actual_page_count} pages, which is below the minimum of {min_pages} pages.",
                    "provenance": "Amazon KDP Minimum Interior Page Count Rules",
                })
            # Check even page count physical requirement
            if actual_page_count % 2 != 0:
                findings.append({
                    "rule_id": "PDF-PAG-003",
                    "category": "PDF_STRUCTURE",
                    "severity": "WARNING",
                    "explanation": f"Interior page count ({actual_page_count}) is odd. KDP physically manufactures even page counts.",
                    "provenance": "Amazon KDP Print Manufacturing Rules",
                })

        # 5. MediaBox Dimensions Verification (within 1.0 pt tolerance)
        if actual_page_count > 0:
            p1 = reader.pages[0]
            w = float(p1.mediabox.width)
            h = float(p1.mediabox.height)

            tol = 1.0  # 1 point tolerance
            if abs(w - expected_width_pt) > tol or abs(h - expected_height_pt) > tol:
                findings.append({
                    "rule_id": "PDF-DIM-001",
                    "category": "PDF_STRUCTURE",
                    "severity": "BLOCKING",
                    "explanation": (
                        f"PDF page dimensions ({w:.1f}pt x {h:.1f}pt) do not match expected MediaBox dimensions "
                        f"({expected_width_pt:.1f}pt x {expected_height_pt:.1f}pt)."
                    ),
                    "provenance": "Amazon KDP Exact Trim Sizing Requirements",
                })

        # 6. Font Embedding Inspection
        embedded_fonts = set()
        unembedded_fonts = set()
        for idx, page in enumerate(reader.pages):
            resources = page.get("/Resources")
            if not resources:
                continue
            fonts = resources.get("/Font")
            if not fonts:
                continue
            for font_key, font_obj in fonts.items():
                try:
                    f_resolved = font_obj.get_object() if hasattr(font_obj, "get_object") else font_obj
                    base_font = str(f_resolved.get("/BaseFont", "Unknown"))

                    descriptors_to_check = []
                    # 1. Direct FontDescriptor (Type1, TrueType)
                    if "/FontDescriptor" in f_resolved:
                        descriptors_to_check.append(f_resolved.get("/FontDescriptor"))
                    # 2. DescendantFonts FontDescriptor (Type0 CID fonts used by WeasyPrint)
                    if "/DescendantFonts" in f_resolved:
                        descendants = f_resolved.get("/DescendantFonts", [])
                        for df in descendants:
                            df_obj = df.get_object() if hasattr(df, "get_object") else df
                            if "/FontDescriptor" in df_obj:
                                descriptors_to_check.append(df_obj.get("/FontDescriptor"))

                    if descriptors_to_check:
                        is_font_embedded = False
                        for descriptor in descriptors_to_check:
                            desc_obj = descriptor.get_object() if hasattr(descriptor, "get_object") else descriptor
                            has_file = any(key in desc_obj for key in ("/FontFile", "/FontFile2", "/FontFile3"))
                            if has_file:
                                is_font_embedded = True
                                break
                        if is_font_embedded:
                            embedded_fonts.add(base_font)
                        else:
                            unembedded_fonts.add(base_font)
                    else:
                        # Base-14 or standard font reference without FontDescriptor / embedded stream
                        unembedded_fonts.add(base_font)
                except Exception:
                    pass

        if unembedded_fonts:
            findings.append({
                "rule_id": "PDF-FNT-001",
                "category": "PDF_STRUCTURE",
                "severity": "WARNING",
                "explanation": f"Fonts not fully embedded (missing /FontFile, /FontFile2, or /FontFile3 stream): {', '.join(sorted(unembedded_fonts))}. Amazon KDP requires all fonts to be fully embedded.",
                "provenance": "Amazon KDP Font Embedding Standards & ISO 32000-1",
            })

        # 7. Image Extraction & Effective DPI Inspection
        image_advisories = []
        for p_idx, page in enumerate(reader.pages):
            try:
                for img_idx, img in enumerate(page.images):
                    try:
                        img_w_px = img.image.width
                        # Physical width assumption: bounded by page printable width
                        render_w_in = (expected_width_pt - 72.0) / 72.0
                        if render_w_in > 0:
                            effective_dpi = img_w_px / render_w_in
                            if effective_dpi < 300.0:
                                image_advisories.append({
                                    "page": p_idx + 1,
                                    "image_name": img.name,
                                    "effective_dpi": round(effective_dpi, 1),
                                })
                    except Exception:
                        pass
            except Exception:
                pass

        for adv in image_advisories:
            findings.append({
                "rule_id": "IMG-DPI-001",
                "category": "IMAGE_QUALITY",
                "severity": "ADVISORY",
                "explanation": f"Page {adv['page']} image '{adv['image_name']}' has effective resolution of {adv['effective_dpi']} DPI (< 300 DPI Amazon KDP recommended standard).",
                "provenance": "Amazon KDP Image Resolution Standard (300 DPI)",
            })

        has_blocking = any(f["severity"] == "BLOCKING" for f in findings)
        return {
            "is_valid": not has_blocking,
            "page_count": actual_page_count,
            "file_size_bytes": file_size_bytes,
            "embedded_fonts": sorted(list(embedded_fonts)),
            "unembedded_fonts": sorted(list(unembedded_fonts)),
            "all_fonts_embedded": len(unembedded_fonts) == 0 and len(embedded_fonts) > 0,
            "image_advisories_count": len(image_advisories),
            "findings": findings,
        }
