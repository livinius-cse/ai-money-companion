import io
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
import pypdf
from decimal import DecimalException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.schemas.preflight import (
    QAFinding,
    CryptographicHashes,
    DocumentVersionInfo,
    PreFlightQAReport,
)
from app.services.hasher import CryptographicHasherService
from app.services.cover_calculation import CoverCalculationService, parse_trim_size_inches
from app.services.interior_compiler import get_gutter_margin_pt
from app.services.quality_validation import QualityValidationService
from app.services.kdp_validator import KDPValidatorService

# Tolerances in points (72 points = 1 inch; 4pt ~= 0.055 inches)
DIMENSION_TOLERANCE_PT = 4.0
MAX_PDF_SIZE_BYTES = 650 * 1024 * 1024


class PreFlightQAService:
    """
    Comprehensive Pre-Flight QA & Verification Service for Amazon KDP Publishing.
    Performs physical PDF verification, manuscript audit, KDP manufacturing compliance,
    metadata validation, and five-way cryptographic integrity.
    """

    @classmethod
    def run_qa(cls, db: Session, book: Book) -> PreFlightQAReport:
        """
        Execute full end-to-end Pre-Flight QA audit across all components.
        Returns immutable structured report with stable rule IDs and severities.
        """
        findings: List[QAFinding] = []

        # 1. Calculate All 5 Cryptographic Hashes & Fetch Components
        hash_data = CryptographicHasherService.compute_all_hashes(db, book)
        interior_doc: Optional[BookDocument] = hash_data["interior_document"]
        cover_doc: Optional[BookDocument] = hash_data["cover_document"]
        interior_bytes: Optional[bytes] = hash_data["interior_bytes"]
        cover_bytes: Optional[bytes] = hash_data["cover_bytes"]
        ai_disclosure: Optional[AIDisclosureAttestation] = hash_data["ai_disclosure"]

        # Fetch chapters & illustrations
        chapters = list(
            db.scalars(
                select(Chapter)
                .where(Chapter.book_id == book.id)
                .order_by(Chapter.chapter_number.asc())
            ).all()
        )
        illustrations = list(
            db.scalars(
                select(Illustration).where(Illustration.book_id == book.id)
            ).all()
        )

        # 2. Audit Manuscript
        cls._validate_manuscript(book, chapters, illustrations, findings)
        cls._validate_illustration_integrity(
            hash_data.get("illustration_errors", []) + hash_data.get("manuscript_errors", []),
            findings,
        )

        # 3. Audit Interior PDF
        actual_interior_pages = cls._validate_interior_pdf(
            book, interior_doc, interior_bytes, hash_data.get("interior_error"), findings
        )

        # 4. Audit Cover PDF
        cls._validate_cover_pdf(
            book, cover_doc, cover_bytes, actual_interior_pages, hash_data.get("cover_error"), findings
        )

        # 5. Audit KDP Metadata & Publishing Configuration
        cls._validate_metadata(book, ai_disclosure, findings)

        # 6. Readability Analysis
        full_text = " ".join([c.content for c in chapters if c.content])
        readability = QualityValidationService.analyze_readability(full_text, language="en")

        # 7. Compute Summary Counts
        blocking_count = sum(1 for f in findings if f.severity == "BLOCKING")
        warning_count = sum(1 for f in findings if f.severity == "WARNING")
        info_count = sum(1 for f in findings if f.severity == "INFO")

        # Ready only if 0 blocking issues AND both interior & cover exist AND hashes are verified
        is_ready = (
            blocking_count == 0
            and interior_doc is not None
            and cover_doc is not None
            and hash_data.get("composite_hash") is not None
        )

        hashes_dto = CryptographicHashes(
            manuscript_hash=hash_data.get("manuscript_hash"),
            metadata_hash=hash_data.get("metadata_hash"),
            interior_hash=hash_data.get("interior_hash"),
            cover_hash=hash_data.get("cover_hash"),
            composite_hash=hash_data.get("composite_hash"),
            hash_scheme_version=hash_data.get("hash_scheme_version", "kdp-sha256-v1"),
        )

        doc_info = DocumentVersionInfo(
            interior_id=interior_doc.id if interior_doc else None,
            interior_version=interior_doc.version if interior_doc else None,
            interior_page_count=actual_interior_pages,
            interior_file_size=interior_doc.file_size_bytes if interior_doc else None,
            cover_id=cover_doc.id if cover_doc else None,
            cover_version=cover_doc.version if cover_doc else None,
            cover_file_size=cover_doc.file_size_bytes if cover_doc else None,
        )

        return PreFlightQAReport(
            report_id=str(uuid.uuid4()),
            book_id=book.id,
            book_title=book.title,
            timestamp=datetime.now(timezone.utc),
            is_ready_for_approval=is_ready,
            blocking_count=blocking_count,
            warning_count=warning_count,
            info_count=info_count,
            findings=findings,
            hashes=hashes_dto,
            document_versions=doc_info,
            ai_disclosure_attested=bool(ai_disclosure and ai_disclosure.author_reviewed),
            readability_summary=readability,
        )

    # -------------------------------------------------------------------------
    # Manuscript Validation
    # -------------------------------------------------------------------------
    @classmethod
    def _validate_manuscript(
        cls,
        book: Book,
        chapters: List[Chapter],
        illustrations: List[Illustration],
        findings: List[QAFinding],
    ) -> None:
        if not chapters:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-001",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation="The book has no chapters configured in Product Studio.",
                    relevant_field="chapters",
                    observed_value=0,
                    remediation="Add content chapters or generate a structured book plan before pre-flight QA.",
                )
            )
            return

        # Check chapter sequence & numbering
        expected_numbers = list(range(1, len(chapters) + 1))
        actual_numbers = [c.chapter_number for c in chapters]
        if actual_numbers != expected_numbers:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-001",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation=f"Chapter numbering is inconsistent or non-sequential: observed {actual_numbers}.",
                    relevant_field="chapters.chapter_number",
                    observed_value=actual_numbers,
                    remediation="Reorder or renumber chapters to form a strict 1..N sequential hierarchy.",
                )
            )

        # Check for empty or incomplete chapters
        empty_chapters = []
        total_words = 0
        for ch in chapters:
            wc = len(ch.content.split()) if ch.content else 0
            total_words += wc
            if not ch.content or not ch.content.strip() or wc < 10:
                empty_chapters.append(f"Chapter {ch.chapter_number} ({ch.title})")

        if empty_chapters:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-002",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation=f"Found {len(empty_chapters)} empty or incomplete chapter(s): {', '.join(empty_chapters[:3])}.",
                    relevant_field="chapters.content",
                    observed_value=empty_chapters,
                    remediation="Write or generate complete manuscript copy for each drafted chapter.",
                )
            )

        # Check front and back matter
        if book.front_matter_pages < 0 or book.back_matter_pages < 0:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-003",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation="Negative front or back matter page counts configured.",
                    relevant_field="book.front_matter_pages",
                    observed_value={"front": book.front_matter_pages, "back": book.back_matter_pages},
                    remediation="Set front matter pages >= 0 and back matter pages >= 0 in book settings.",
                )
            )

        # Check illustration status and asset existence
        unapproved_ills = [
            ill.id for ill in illustrations if ill.status != "APPROVED_FINAL"
        ]
        if unapproved_ills:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-004",
                    category="MANUSCRIPT",
                    severity="WARNING",
                    explanation=f"{len(unapproved_ills)} illustration asset(s) are not in APPROVED_FINAL status.",
                    relevant_field="illustrations.status",
                    observed_value=len(unapproved_ills),
                    remediation="Review and approve final illustration assets in the Illustration Studio.",
                )
            )

        # Check total manuscript length
        if total_words < 100:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-005",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation=f"Total manuscript length is only {total_words} words, which does not meet minimum publishing standards.",
                    relevant_field="chapters.total_words",
                    observed_value=total_words,
                    remediation="Flesh out manuscript sections with complete content before proceeding.",
                )
            )
        else:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-005",
                    category="MANUSCRIPT",
                    severity="INFO",
                    explanation=f"Total manuscript length is {total_words:,} words across {len(chapters)} chapters.",
                    relevant_field="chapters.total_words",
                    observed_value=total_words,
                    remediation="No action required.",
                )
            )

        # Check Amazon policy violations
        chap_dicts = [
            {"chapter_number": c.chapter_number, "title": c.title, "content": c.content}
            for c in chapters
        ]
        policy_findings = QualityValidationService.audit_manuscript_content(
            book_title=book.title,
            chapters=chap_dicts,
            cover_texts=[book.title, book.subtitle or "", book.topic or ""],
        )
        for pf in policy_findings:
            raw_sev = pf.get("severity", "WARNING")
            sev = "INFO" if raw_sev == "ADVISORY" else raw_sev
            if sev not in ("BLOCKING", "WARNING", "INFO"):
                sev = "WARNING"
            findings.append(
                QAFinding(
                    rule_id=pf.get("rule_id", "QA-MS-POL"),
                    category="MANUSCRIPT",
                    severity=sev,
                    explanation=pf.get("explanation", "Potential Amazon policy violation"),
                    relevant_field="manuscript_content",
                    observed_value=pf.get("match_snippet"),
                    remediation=pf.get("correction", "Revise content to comply with Amazon KDP publishing policies."),
                )
            )

    @classmethod
    def _validate_illustration_integrity(
        cls,
        illustration_errors: List[str],
        findings: List[QAFinding],
    ) -> None:
        for error in illustration_errors:
            findings.append(
                QAFinding(
                    rule_id="QA-MS-006",
                    category="MANUSCRIPT",
                    severity="BLOCKING",
                    explanation=error,
                    relevant_field="illustrations.asset",
                    observed_value=None,
                    remediation="Replace or re-upload the approved illustration asset, then rerun pre-flight QA.",
                )
            )

    # -------------------------------------------------------------------------
    # Interior PDF Validation
    # -------------------------------------------------------------------------
    @classmethod
    def _validate_interior_pdf(
        cls,
        book: Book,
        interior_doc: Optional[BookDocument],
        interior_bytes: Optional[bytes],
        read_error: Optional[str],
        findings: List[QAFinding],
    ) -> Optional[int]:
        if interior_doc and interior_doc.file_size_bytes > MAX_PDF_SIZE_BYTES:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-008",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation="Interior PDF exceeds the 650 MB file-size limit.",
                    relevant_field="documents.interior.file_size_bytes",
                    observed_value=interior_doc.file_size_bytes,
                    remediation="Reduce embedded image sizes or remove unnecessary content, then recompile the interior.",
                )
            )

        if not interior_doc:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-001",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=read_error or "No compiled interior PDF found for this book.",
                    relevant_field="documents.interior",
                    observed_value=None,
                    remediation="Compile interior PDF in Interior Layout Studio before running Pre-Flight QA.",
                )
            )
            return None

        # Check file integrity
        if read_error:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-009",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=f"Physical interior file integrity failure: {read_error}",
                    relevant_field="documents.interior.sha256_hash",
                    observed_value=None,
                    remediation="Recompile interior PDF to regenerate clean, verifiable disk bytes.",
                )
            )
            return None
        if not interior_bytes:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-001",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation="Stored interior PDF bytes are unavailable.",
                    relevant_field="documents.interior",
                    observed_value=None,
                    remediation="Regenerate the interior document and rerun pre-flight QA.",
                )
            )
            return None

        # Check file size limit (650 MB)
        file_size = len(interior_bytes)
        if file_size > MAX_PDF_SIZE_BYTES:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-008",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=f"Interior PDF size ({file_size / (1024*1024):.1f}MB) exceeds Amazon KDP 650MB limit.",
                    relevant_field="documents.interior.file_size_bytes",
                    observed_value=file_size,
                    remediation="Compress high-resolution interior artwork or reduce page assets.",
                )
            )

        # Inspect PDF structure with pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(interior_bytes))
        except Exception as e:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-001",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=f"Failed to parse interior PDF document: {str(e)}",
                    relevant_field="documents.interior.bytes",
                    observed_value=None,
                    remediation="Recompile interior PDF using standard PDF/X-1a or PDF 1.7 specifications.",
                )
            )
            return None

        # Encryption check
        if reader.is_encrypted:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-007",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation="Interior PDF is encrypted or password-protected. Amazon KDP strictly rejects protected PDFs.",
                    relevant_field="documents.interior.is_encrypted",
                    observed_value=True,
                    remediation="Recompile interior PDF without password protection or encryption.",
                )
            )
            return None

        actual_page_count = len(reader.pages)
        if actual_page_count != interior_doc.page_count:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-010",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation="The PDF page count differs from the persisted document record.",
                    relevant_field="documents.interior.page_count",
                    observed_value={
                        "pdf": actual_page_count,
                        "record": interior_doc.page_count,
                    },
                    remediation="Regenerate the interior document so its persisted metadata matches the PDF.",
                )
            )

        # Minimum page count: Paperback >= 24, Hardcover >= 75
        is_hardcover = book.print_format.lower() == "hardcover"
        min_pages = 75 if is_hardcover else 24
        if actual_page_count < min_pages:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-002",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=f"Amazon KDP requires minimum {min_pages} pages for {book.print_format}. Observed only {actual_page_count} page(s).",
                    relevant_field="documents.interior.page_count",
                    observed_value=actual_page_count,
                    remediation=f"Add manuscript content or expand chapter allocations to reach at least {min_pages} pages.",
                )
            )
        else:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-002",
                    category="INTERIOR",
                    severity="INFO",
                    explanation=f"Interior PDF satisfies Amazon KDP minimum page count threshold ({actual_page_count} >= {min_pages} pages).",
                    relevant_field="documents.interior.page_count",
                    observed_value=actual_page_count,
                    remediation="No action required.",
                )
            )

        # Even page count requirement
        if actual_page_count % 2 != 0:
            findings.append(
                QAFinding(
                    rule_id="QA-INT-003",
                    category="INTERIOR",
                    severity="BLOCKING",
                    explanation=f"Interior PDF page count must be even for physical book manufacturing. Observed {actual_page_count} pages (odd).",
                    relevant_field="documents.interior.page_count",
                    observed_value=actual_page_count,
                    remediation="Recompile interior PDF. The compiler will automatically insert a blank back leaf to ensure even page count.",
                )
            )

        # Trim dimensions check
        if actual_page_count > 0:
            page_dimensions = [
                (float(page.mediabox.width), float(page.mediabox.height))
                for page in reader.pages
            ]
            w_pt, h_pt = page_dimensions[0]

            try:
                trim_w_in, trim_h_in = parse_trim_size_inches(book.trim_size)
                exp_w = float(trim_w_in * 72)
                exp_h = float(trim_h_in * 72)
                if interior_doc.bleed_config not in {"no_bleed", "bleed_0.125"}:
                    findings.append(
                        QAFinding(
                            rule_id="QA-INT-005",
                            category="INTERIOR",
                            severity="BLOCKING",
                            explanation="The persisted interior bleed configuration is not recognized.",
                            relevant_field="documents.interior.bleed_config",
                            observed_value=interior_doc.bleed_config,
                            remediation="Regenerate the interior using the supported no-bleed or 0.125-inch bleed setting.",
                        )
                    )
                is_bleed = interior_doc.bleed_config == "bleed_0.125"
                if is_bleed:
                    exp_w += 0.125 * 72.0
                    exp_h += 0.250 * 72.0

                w_diff = abs(w_pt - exp_w)
                h_diff = abs(h_pt - exp_h)
                inconsistent_pages = [
                    index + 1
                    for index, (page_w, page_h) in enumerate(page_dimensions)
                    if abs(page_w - exp_w) > DIMENSION_TOLERANCE_PT
                    or abs(page_h - exp_h) > DIMENSION_TOLERANCE_PT
                ]
                if w_diff > DIMENSION_TOLERANCE_PT or h_diff > DIMENSION_TOLERANCE_PT or inconsistent_pages:
                    findings.append(
                        QAFinding(
                            rule_id="QA-INT-004",
                            category="INTERIOR",
                            severity="BLOCKING",
                            explanation=f"Interior PDF page dimensions do not consistently match the expected KDP trim {book.trim_size} ({exp_w:.1f}pt x {exp_h:.1f}pt).",
                            relevant_field="documents.interior.dimensions",
                            observed_value={
                                "first_page": {"width_pt": round(w_pt, 1), "height_pt": round(h_pt, 1)},
                                "inconsistent_pages": inconsistent_pages[:25],
                            },
                            remediation="Recompile interior PDF with correct trim size selection.",
                        )
                    )
                generation_metadata = interior_doc.generation_metadata or {}
                if (
                    "gutter_margin_pt" in generation_metadata
                    and "outside_margin_pt" in generation_metadata
                ):
                    estimated_pages = max(24, book.target_page_count or 100)
                    expected_gutter = get_gutter_margin_pt(estimated_pages)
                    expected_outside = 36.0
                    gutter = generation_metadata["gutter_margin_pt"]
                    outside = generation_metadata["outside_margin_pt"]
                    if (
                        not isinstance(gutter, (int, float))
                        or not isinstance(outside, (int, float))
                        or abs(gutter - expected_gutter) > DIMENSION_TOLERANCE_PT
                        or abs(outside - expected_outside) > DIMENSION_TOLERANCE_PT
                    ):
                        findings.append(
                            QAFinding(
                                rule_id="QA-INT-012",
                                category="INTERIOR",
                                severity="BLOCKING",
                                explanation="Persisted interior margin and gutter measurements do not match the M4 layout requirements.",
                                relevant_field="documents.interior.generation_metadata",
                                observed_value={
                                    "gutter_margin_pt": gutter,
                                    "outside_margin_pt": outside,
                                    "expected_gutter_margin_pt": expected_gutter,
                                    "expected_outside_margin_pt": expected_outside,
                                },
                                remediation="Regenerate the interior with the existing M4 gutter and margin calculation.",
                            )
                        )
                else:
                    findings.append(
                        QAFinding(
                            rule_id="QA-INT-012",
                            category="INTERIOR",
                            severity="WARNING",
                            explanation="The interior document has no persisted margin and gutter measurements to verify.",
                            relevant_field="documents.interior.generation_metadata",
                            observed_value=None,
                            remediation="Regenerate the interior using the M4 layout engine to record margin and gutter checks.",
                        )
                    )
            except (ValueError, DecimalException):
                findings.append(
                    QAFinding(
                        rule_id="QA-INT-004",
                        category="INTERIOR",
                        severity="BLOCKING",
                        explanation=f"Configured trim size '{book.trim_size}' cannot be validated.",
                        relevant_field="book.trim_size",
                        observed_value=book.trim_size,
                        remediation="Choose a supported trim size and regenerate the interior PDF.",
                    )
                )

            # Check embedded font programs; Base-14 fonts without font streams are not embedded.
            has_fonts = False
            unembedded_fonts: List[str] = []
            for page in reader.pages:
                resources = page.get("/Resources")
                if not resources:
                    continue
                fonts = resources.get("/Font")
                if not fonts:
                    continue
                for font_name, font_ref in fonts.get_object().items():
                    has_fonts = True
                    font = font_ref.get_object()
                    if font.get("/Subtype") == "/Type3":
                        continue
                    descriptor_ref = font.get("/FontDescriptor")
                    descriptor = descriptor_ref.get_object() if descriptor_ref else None
                    if not descriptor or not any(
                        descriptor.get(key)
                        for key in ("/FontFile", "/FontFile2", "/FontFile3")
                    ):
                        unembedded_fonts.append(str(font_name))

            if not has_fonts or unembedded_fonts:
                findings.append(
                    QAFinding(
                        rule_id="QA-INT-006",
                        category="INTERIOR",
                        severity="WARNING",
                        explanation=(
                            "No fonts were found in the interior PDF."
                            if not has_fonts
                            else "One or more interior PDF fonts do not have embedded font programs."
                        ),
                        relevant_field="documents.interior.fonts",
                        observed_value=unembedded_fonts[:25],
                        remediation="Ensure font files are correctly embedded when compiling interior.",
                    )
                )

        for advisory in (interior_doc.generation_metadata or {}).get("dpi_advisories", []):
            findings.append(
                QAFinding(
                    rule_id="QA-INT-011",
                    category="INTERIOR",
                    severity="WARNING",
                    explanation=str(advisory.get("warning", "An illustration is below 300 DPI.")),
                    relevant_field="illustrations.resolution",
                    observed_value=advisory.get("effective_dpi"),
                    remediation="Replace or resize the source illustration to provide at least 300 effective DPI.",
                )
            )

        return actual_page_count

    # -------------------------------------------------------------------------
    # Cover PDF Validation
    # -------------------------------------------------------------------------
    @classmethod
    def _validate_cover_pdf(
        cls,
        book: Book,
        cover_doc: Optional[BookDocument],
        cover_bytes: Optional[bytes],
        interior_page_count: Optional[int],
        read_error: Optional[str],
        findings: List[QAFinding],
    ) -> None:
        if cover_doc and cover_doc.file_size_bytes > MAX_PDF_SIZE_BYTES:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-007",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="Cover PDF exceeds the 650 MB file-size limit.",
                    relevant_field="documents.cover.file_size_bytes",
                    observed_value=cover_doc.file_size_bytes,
                    remediation="Reduce embedded artwork size and regenerate the cover PDF.",
                )
            )

        if not cover_doc:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-001",
                    category="COVER",
                    severity="BLOCKING",
                    explanation=read_error or "No compiled full-jacket cover PDF found for this book.",
                    relevant_field="documents.cover",
                    observed_value=None,
                    remediation="Compile full-jacket cover PDF in Cover Design Studio before running Pre-Flight QA.",
                )
            )
            return

        if read_error:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-006",
                    category="COVER",
                    severity="BLOCKING",
                    explanation=f"Physical cover file integrity failure: {read_error}",
                    relevant_field="documents.cover.sha256_hash",
                    observed_value=None,
                    remediation="Recompile cover PDF to regenerate clean, verifiable disk bytes.",
                )
            )
            return
        if not cover_bytes:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-001",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="Stored cover PDF bytes are unavailable.",
                    relevant_field="documents.cover",
                    observed_value=None,
                    remediation="Regenerate the cover document and rerun pre-flight QA.",
                )
            )
            return

        try:
            reader = pypdf.PdfReader(io.BytesIO(cover_bytes))
        except Exception as e:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-001",
                    category="COVER",
                    severity="BLOCKING",
                    explanation=f"Failed to parse cover PDF document: {str(e)}",
                    relevant_field="documents.cover.bytes",
                    observed_value=None,
                    remediation="Recompile cover PDF using standard PDF engine.",
                )
            )
            return

        # Encryption check
        if reader.is_encrypted:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-006",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="Cover PDF is encrypted. Amazon KDP requires unencrypted PDFs.",
                    relevant_field="documents.cover.is_encrypted",
                    observed_value=True,
                    remediation="Recompile cover PDF without password protection or encryption.",
                )
            )
            return

        # Single page requirement
        if len(reader.pages) != 1:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-002",
                    category="COVER",
                    severity="BLOCKING",
                    explanation=f"Amazon KDP full-jacket cover PDF must contain exactly 1 composite page. Observed {len(reader.pages)} pages.",
                    relevant_field="documents.cover.page_count",
                    observed_value=len(reader.pages),
                    remediation="Recompile cover PDF as a single full-jacket sheet (back, spine, and front).",
                )
            )
            return

        if len(reader.pages) != cover_doc.page_count:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-008",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="The cover PDF page count differs from the persisted document record.",
                    relevant_field="documents.cover.page_count",
                    observed_value={"pdf": len(reader.pages), "record": cover_doc.page_count},
                    remediation="Regenerate the cover so persisted metadata matches the actual PDF.",
                )
            )

        # Spine and Dimension Check
        page = reader.pages[0]
        actual_w = float(page.mediabox.width)
        actual_h = float(page.mediabox.height)
        if (
            abs(actual_w - cover_doc.width_pt) > DIMENSION_TOLERANCE_PT
            or abs(actual_h - cover_doc.height_pt) > DIMENSION_TOLERANCE_PT
        ):
            findings.append(
                QAFinding(
                    rule_id="QA-COV-009",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="Cover PDF dimensions differ from the persisted document record.",
                    relevant_field="documents.cover.dimensions",
                    observed_value={
                        "pdf": {"width_pt": actual_w, "height_pt": actual_h},
                        "record": {
                            "width_pt": cover_doc.width_pt,
                            "height_pt": cover_doc.height_pt,
                        },
                    },
                    remediation="Regenerate the cover so persisted metadata matches the actual PDF.",
                )
            )

        pages_to_calc = interior_page_count if interior_page_count else book.target_page_count
        try:
            calc = CoverCalculationService.calculate_full_jacket_cover(
                print_format=book.print_format,
                trim_size=book.trim_size,
                paper_type=book.paper_type,
                interior_page_count=pages_to_calc,
            )
        except (ValueError, DecimalException):
            findings.append(
                QAFinding(
                    rule_id="QA-COV-004",
                    category="COVER",
                    severity="BLOCKING",
                    explanation="The cover dimensions cannot be calculated from the persisted print configuration.",
                    relevant_field="book.print_format",
                    observed_value={
                        "print_format": book.print_format,
                        "trim_size": book.trim_size,
                        "paper_type": book.paper_type,
                    },
                    remediation="Choose a supported print format, trim size, and paper type, then regenerate the cover.",
                )
            )
            return

        exp_w = calc.full_cover_width_pt
        exp_h = calc.full_cover_height_pt

        w_diff = abs(actual_w - exp_w)
        h_diff = abs(actual_h - exp_h)

        if w_diff > DIMENSION_TOLERANCE_PT or h_diff > DIMENSION_TOLERANCE_PT:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-003",
                    category="COVER",
                    severity="BLOCKING",
                    explanation=(
                        f"Cover PDF dimensions ({actual_w:.1f}pt x {actual_h:.1f}pt) do not match calculated KDP jacket "
                        f"({exp_w:.1f}pt x {exp_h:.1f}pt) for {pages_to_calc} pages."
                    ),
                    relevant_field="documents.cover.dimensions",
                    observed_value={"actual_w": round(actual_w, 1), "actual_h": round(actual_h, 1)},
                    remediation="Recompile cover PDF to synchronize spine thickness and bleed with interior page count.",
                )
            )
        else:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-003",
                    category="COVER",
                    severity="INFO",
                    explanation=f"Cover dimensions ({actual_w:.1f}pt x {actual_h:.1f}pt) match KDP full-jacket requirements.",
                    relevant_field="documents.cover.dimensions",
                    observed_value={"width_pt": round(actual_w, 1), "height_pt": round(actual_h, 1)},
                    remediation="No action required.",
                )
            )

        # Spine text eligibility rule: Amazon KDP prohibits spine text on books < 80 pages
        if pages_to_calc < 80:
            findings.append(
                QAFinding(
                    rule_id="QA-COV-005",
                    category="COVER",
                    severity="WARNING",
                    explanation=f"Interior has {pages_to_calc} pages (< 80). Amazon KDP does not permit readable spine text on thin spines.",
                    relevant_field="documents.cover.spine_text",
                    observed_value=pages_to_calc,
                    remediation="Verify that spine text is disabled for books under 80 pages.",
                )
            )

    # -------------------------------------------------------------------------
    # Metadata & Publishing Config Validation
    # -------------------------------------------------------------------------
    @classmethod
    def _validate_metadata(
        cls,
        book: Book,
        ai_disclosure: Optional[AIDisclosureAttestation],
        findings: List[QAFinding],
    ) -> None:
        # Title validation
        if not book.title or len(book.title.strip()) < 1:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-001",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation="Book title is required.",
                    relevant_field="book.title",
                    observed_value="",
                    remediation="Provide a valid book title in Book Concept.",
                )
            )
        elif len(book.title) > 200:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-002",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation=f"Book title exceeds Amazon KDP 200-character limit ({len(book.title)} chars).",
                    relevant_field="book.title",
                    observed_value=len(book.title),
                    remediation="Shorten book title to 200 characters or fewer.",
                )
            )

        # Subtitle validation
        if book.subtitle and len(book.subtitle) > 200:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-002",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation=f"Book subtitle exceeds Amazon KDP 200-character limit ({len(book.subtitle)} chars).",
                    relevant_field="book.subtitle",
                    observed_value=len(book.subtitle),
                    remediation="Shorten book subtitle to 200 characters or fewer.",
                )
            )

        # Topic & Concept
        if not book.topic or len(book.topic.strip()) < 1:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-001",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation="Core book topic is missing.",
                    relevant_field="book.topic",
                    observed_value="",
                    remediation="Specify the publishing niche and topic in Book Concept.",
                )
            )

        # Marketplace check
        valid_marketplaces = [
            "amazon_com", "amazon_co_uk", "amazon_de", "amazon_fr",
            "amazon_es", "amazon_it", "amazon_nl", "amazon_pl",
            "amazon_se", "amazon_co_jp", "amazon_ca", "amazon_com_au"
        ]
        if book.marketplace not in valid_marketplaces:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-003",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation=f"Invalid marketplace '{book.marketplace}'. Must be an approved Amazon KDP marketplace.",
                    relevant_field="book.marketplace",
                    observed_value=book.marketplace,
                    remediation=f"Select one of: {', '.join(valid_marketplaces)}.",
                )
            )

        # AI-Generated Content Disclosure Check
        if not ai_disclosure or not ai_disclosure.author_reviewed:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-004",
                    category="METADATA",
                    severity="BLOCKING",
                    explanation="Amazon KDP requires mandatory disclosure of AI-generated content (text, artwork, translations). No confirmed disclosure found.",
                    relevant_field="ai_disclosure.author_reviewed",
                    observed_value=False,
                    remediation="Complete and confirm your AI Content Disclosure in the AI Settings or Pre-Flight panel.",
                )
            )
        else:
            findings.append(
                QAFinding(
                    rule_id="QA-MET-004",
                    category="METADATA",
                    severity="INFO",
                    explanation=f"Amazon KDP AI Content Disclosure is confirmed by author ({ai_disclosure.author_attested_at.strftime('%Y-%m-%d %H:%M UTC') if ai_disclosure.author_attested_at else 'attested'}).",
                    relevant_field="ai_disclosure.author_reviewed",
                    observed_value=True,
                    remediation="No action required.",
                )
            )
