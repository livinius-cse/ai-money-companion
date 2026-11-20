import hashlib
import json
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, select

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.core.storage import LocalAssetStorage, detect_image_type

HASH_SCHEME_VERSION = "kdp-sha256-v2"


def nfc_normalize(val: Any) -> Any:
    """Recursively normalize all string values to Unicode NFC."""
    if isinstance(val, str):
        return unicodedata.normalize("NFC", val)
    elif isinstance(val, dict):
        return {nfc_normalize(k): nfc_normalize(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [nfc_normalize(item) for item in val]
    return val


def canonical_json_bytes(data: Any) -> bytes:
    """
    Serialize data to deterministic, canonical UTF-8 JSON bytes:
    - Unicode NFC normalization
    - Sorted keys
    - Compact separators (no superfluous whitespace)
    - UTF-8 encoding
    """
    normalized = nfc_normalize(data)
    json_str = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return json_str.encode("utf-8")


def calculate_sha256_hex(data: bytes) -> str:
    """Calculate hex-encoded SHA-256 digest of raw binary bytes."""
    return hashlib.sha256(data).hexdigest()


class CryptographicHasherService:
    """
    Deterministic Five-Way Cryptographic Hashing Engine.
    Computes immutable SHA-256 hashes across:
    1. Manuscript content & approved illustrations.
    2. Persisted KDP metadata and manufacturing parameters.
    3. Actual stored interior PDF bytes.
    4. Actual stored cover PDF bytes.
    5. Composite manifest combining all 4 component hashes.
    """

    @classmethod
    def compute_manuscript_hash(
        cls,
        book: Book,
        chapters: List[Chapter],
        approved_illustrations: List[Illustration],
        illustration_hashes: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Deterministic SHA-256 hash of ordered manuscript chapters and approved illustrations.
        Excludes mutable timestamps, database IDs of chapters, and draft statuses.
        """
        sorted_chapters = sorted(chapters, key=lambda c: (c.chapter_number, c.id))
        chapters_payload = [
            {
                "chapter_number": ch.chapter_number,
                "chapter_type": ch.chapter_type,
                "title": ch.title.strip(),
                "content": ch.content,
                "allocated_pages": ch.allocated_pages,
            }
            for ch in sorted_chapters
        ]

        sorted_illustrations = sorted(approved_illustrations, key=lambda ill: ill.id)
        illustrations_payload = [
            {
                "id": ill.id,
                "chapter_id": ill.chapter_id,
                "prompt": ill.prompt.strip(),
                "description": (ill.description or "").strip(),
                "position_description": (ill.position_description or "").strip(),
                "sha256_hash": (
                    illustration_hashes[ill.id]
                    if illustration_hashes is not None
                    else ill.sha256_hash or ""
                ),
            }
            for ill in sorted_illustrations
        ]

        canonical_payload = {
            "component": "manuscript_and_illustrations",
            "hash_scheme_version": HASH_SCHEME_VERSION,
            "book_id": book.id,
            "chapters": chapters_payload,
            "approved_illustrations": illustrations_payload,
        }

        return calculate_sha256_hex(canonical_json_bytes(canonical_payload))

    @classmethod
    def compute_metadata_hash(
        cls,
        book: Book,
        ai_disclosure: Optional[AIDisclosureAttestation] = None,
    ) -> str:
        """
        Deterministic SHA-256 hash of persisted KDP metadata and manufacturing configuration.
        Excludes volatile timestamps and database record IDs.
        """
        disclosure_payload = None
        if ai_disclosure:
            disclosure_payload = {
                "text_creation_method": ai_disclosure.text_creation_method,
                "text_tools_used": sorted(ai_disclosure.text_tools_used or []),
                "text_editing_extent": ai_disclosure.text_editing_extent,
                "image_creation_method": ai_disclosure.image_creation_method,
                "image_tools_used": sorted(ai_disclosure.image_tools_used or []),
                "image_editing_extent": ai_disclosure.image_editing_extent,
                "translation_creation_method": ai_disclosure.translation_creation_method,
                "translation_tools_used": sorted(ai_disclosure.translation_tools_used or []),
                "translation_editing_extent": ai_disclosure.translation_editing_extent,
            }

        canonical_payload = {
            "component": "kdp_metadata_and_publishing_config",
            "hash_scheme_version": HASH_SCHEME_VERSION,
            "book_id": book.id,
            "title": book.title.strip(),
            "subtitle": (book.subtitle or "").strip(),
            "topic": book.topic.strip(),
            "book_concept": (book.book_concept or "").strip(),
            "target_audience": (book.target_audience or "").strip(),
            "target_reader_profile": (book.target_reader_profile or "").strip(),
            "book_type": book.book_type,
            "print_format": book.print_format,
            "marketplace": book.marketplace,
            "trim_size": book.trim_size,
            "paper_type": book.paper_type,
            "target_page_count": book.target_page_count,
            "front_matter_pages": book.front_matter_pages,
            "back_matter_pages": book.back_matter_pages,
            "ai_disclosure": disclosure_payload,
        }

        return calculate_sha256_hex(canonical_json_bytes(canonical_payload))

    @classmethod
    def compute_document_bytes_hash(cls, document: Optional[BookDocument]) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
        """
        Re-read actual stored PDF bytes directly from disk storage and calculate SHA-256.
        Never trusts recorded database hashes without verifying the stored bytes.
        Returns: (sha256_hex, raw_bytes, error_message)
        """
        if not document or not document.storage_key:
            return None, None, "Document record or storage key does not exist"

        try:
            file_path = LocalAssetStorage.get_document_path(document.storage_key)
            actual_size = file_path.stat().st_size
            if actual_size <= 0 or actual_size > 650 * 1024 * 1024:
                return None, None, "Document file size is outside the permitted range"
            if actual_size != document.file_size_bytes:
                return None, None, "Stored file size differs from the recorded document size"

            with open(file_path, "rb") as f:
                raw_bytes = f.read()

            if not raw_bytes.startswith(b"%PDF-"):
                return None, None, "Stored document is not a PDF"

            computed_sha = calculate_sha256_hex(raw_bytes)

            # Strict integrity check against stored document metadata
            if len(document.sha256_hash) != 64 or computed_sha != document.sha256_hash.lower():
                return None, None, "Stored PDF SHA-256 differs from the recorded document hash"

            return computed_sha, raw_bytes, None
        except (HTTPException, OSError, ValueError):
            return None, None, "Stored document file is unavailable or unreadable"

    @classmethod
    def compute_composite_hash(
        cls,
        book_id: str,
        manuscript_hash: str,
        metadata_hash: str,
        interior_hash: str,
        cover_hash: str,
    ) -> str:
        """
        Deterministic composite SHA-256 hash combining all 4 verified component hashes
        under explicit hash scheme versioning.
        """
        canonical_manifest = {
            "hash_scheme_version": HASH_SCHEME_VERSION,
            "manuscript_hash": manuscript_hash,
            "metadata_hash": metadata_hash,
            "interior_hash": interior_hash,
            "cover_hash": cover_hash,
        }
        return calculate_sha256_hex(canonical_json_bytes(canonical_manifest))

    @classmethod
    def compute_all_hashes(
        cls,
        db: Session,
        book: Book,
    ) -> Dict[str, Any]:
        """
        Calculate all five cryptographic hashes for the current book state.
        Returns dictionary containing all 5 hashes, document references, raw bytes, and any read errors.
        """
        # 1. Fetch ordered chapters
        chapters = db.scalars(
            select(Chapter)
            .where(Chapter.book_id == book.id)
            .order_by(Chapter.chapter_number.asc())
        ).all()

        manuscript_errors = [
            f"Chapter {chapter.id} is associated with a different owner"
            for chapter in chapters
            if chapter.owner_id != book.owner_id
        ]

        # 2. Fetch approved illustrations
        approved_illustrations = db.scalars(
            select(Illustration)
            .where(
                Illustration.book_id == book.id,
                Illustration.status == "APPROVED_FINAL",
            )
            .order_by(Illustration.id.asc())
        ).all()

        manuscript_errors.extend(
            f"Approved illustration {illustration.id} is associated with a different owner"
            for illustration in approved_illustrations
            if illustration.owner_id != book.owner_id
        )

        verified_illustration_hashes: Dict[str, str] = {}
        illustration_errors: List[str] = []
        for illustration in approved_illustrations:
            if not illustration.storage_key or not illustration.sha256_hash:
                illustration_errors.append(
                    f"Approved illustration {illustration.id} is missing its asset or recorded hash"
                )
                continue
            try:
                asset_path = LocalAssetStorage.get_asset_path(illustration.storage_key)
                asset_size = asset_path.stat().st_size
                if illustration.file_size_bytes is not None and asset_size != illustration.file_size_bytes:
                    illustration_errors.append(
                        f"Approved illustration {illustration.id} has a recorded size mismatch"
                    )
                    continue
                asset_bytes = asset_path.read_bytes()
                asset_hash = calculate_sha256_hex(asset_bytes)
            except (HTTPException, OSError, ValueError):
                illustration_errors.append(
                    f"Approved illustration {illustration.id} asset is unavailable or unreadable"
                )
                continue

            if asset_hash != illustration.sha256_hash.lower():
                illustration_errors.append(
                    f"Approved illustration {illustration.id} hash does not match its stored asset"
                )
                continue
            if not detect_image_type(asset_bytes):
                illustration_errors.append(
                    f"Approved illustration {illustration.id} is not a supported image asset"
                )
                continue
            verified_illustration_hashes[illustration.id] = asset_hash

        # 3. Fetch latest AI disclosure
        ai_disclosure = db.scalar(
            select(AIDisclosureAttestation)
            .where(AIDisclosureAttestation.user_id == book.owner_id)
            .order_by(AIDisclosureAttestation.created_at.desc())
        )

        # 4. Fetch latest compiled interior & cover documents
        latest_interior = db.scalar(
            select(BookDocument)
            .where(
                BookDocument.book_id == book.id,
                BookDocument.owner_id == book.owner_id,
                BookDocument.document_type == "INTERIOR",
                BookDocument.status == "GENERATED",
            )
            .order_by(desc(BookDocument.version), desc(BookDocument.created_at), desc(BookDocument.id))
        )

        latest_cover = db.scalar(
            select(BookDocument)
            .where(
                BookDocument.book_id == book.id,
                BookDocument.owner_id == book.owner_id,
                BookDocument.document_type == "COVER",
                BookDocument.status == "GENERATED",
            )
            .order_by(desc(BookDocument.version), desc(BookDocument.created_at), desc(BookDocument.id))
        )

        manuscript_hash = None
        if not illustration_errors and not manuscript_errors:
            manuscript_hash = cls.compute_manuscript_hash(
                book,
                list(chapters),
                list(approved_illustrations),
                verified_illustration_hashes,
            )
        metadata_hash = cls.compute_metadata_hash(book, ai_disclosure)

        interior_hash, interior_bytes, interior_err = cls.compute_document_bytes_hash(latest_interior)
        cover_hash, cover_bytes, cover_err = cls.compute_document_bytes_hash(latest_cover)

        composite_hash = None
        if manuscript_hash and metadata_hash and interior_hash and cover_hash:
            composite_hash = cls.compute_composite_hash(
                book_id=book.id,
                manuscript_hash=manuscript_hash,
                metadata_hash=metadata_hash,
                interior_hash=interior_hash,
                cover_hash=cover_hash,
            )

        return {
            "hash_scheme_version": HASH_SCHEME_VERSION,
            "manuscript_hash": manuscript_hash,
            "metadata_hash": metadata_hash,
            "interior_hash": interior_hash,
            "cover_hash": cover_hash,
            "composite_hash": composite_hash,
            "interior_document": latest_interior,
            "cover_document": latest_cover,
            "interior_bytes": interior_bytes,
            "cover_bytes": cover_bytes,
            "interior_error": interior_err,
            "cover_error": cover_err,
            "ai_disclosure": ai_disclosure,
            "illustration_errors": illustration_errors,
            "manuscript_errors": manuscript_errors,
        }
