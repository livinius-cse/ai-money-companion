import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Tuple, Optional
from fastapi import HTTPException, status
from app.core.config import settings

# 10 MB maximum upload size
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

# Supported image types and their signature verification functions
ALLOWED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def detect_image_type(file_bytes: bytes) -> Optional[Tuple[str, str]]:
    """
    Validate binary magic signatures against known safe image formats.
    Returns (mime_type, extension) if valid, None otherwise.
    """
    if len(file_bytes) < 12:
        return None

    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"

    # JPEG signature: FF D8 FF
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"

    # WebP signature: RIFF .... WEBP
    if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return "image/webp", ".webp"

    return None


def calculate_sha256(file_bytes: bytes) -> str:
    """Calculate hex-encoded SHA-256 checksum of raw binary data."""
    return hashlib.sha256(file_bytes).hexdigest()


class LocalAssetStorage:
    """
    Private local asset storage manager.
    Prevents path traversal, enforces storage directory containment,
    and isolates assets by book and resource ID.
    """

    @classmethod
    def get_base_dir(cls) -> Path:
        base = Path(settings.STORAGE_DIR).resolve() / "illustrations"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def save_illustration_asset(
        cls,
        book_id: str,
        illustration_id: str,
        file_bytes: bytes,
        mime_type: str,
    ) -> Tuple[str, int, str]:
        """
        Securely save asset bytes to disk.
        Returns: (storage_key, file_size_bytes, sha256_hash)
        """
        if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed upload limit of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        detected = detect_image_type(file_bytes)
        if not detected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file signature. Only valid PNG, JPEG, and WebP images are permitted.",
            )

        detected_mime, extension = detected
        sha256 = calculate_sha256(file_bytes)

        # Secure non-guessable storage key without user-controlled filenames
        random_suffix = uuid.uuid4().hex[:12]
        relative_path = f"{book_id}/{illustration_id}_{random_suffix}{extension}"

        base_dir = cls.get_base_dir()
        dest_path = (base_dir / relative_path).resolve()

        # Strict path traversal defense
        if not dest_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid storage destination path.",
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return relative_path, len(file_bytes), sha256

    @classmethod
    def get_asset_path(cls, storage_key: str) -> Path:
        """Resolve and verify storage path for an existing asset."""
        base_dir = cls.get_base_dir()
        target_path = (base_dir / storage_key).resolve()

        if not target_path.is_relative_to(base_dir) or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Illustration asset file not found.",
            )

        return target_path

    @classmethod
    def delete_asset(cls, storage_key: Optional[str]) -> bool:
        """Safely delete asset file from disk if it exists."""
        if not storage_key:
            return False
        try:
            base_dir = cls.get_base_dir()
            target_path = (base_dir / storage_key).resolve()
            if target_path.is_relative_to(base_dir) and target_path.is_file():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False

    @classmethod
    def get_documents_base_dir(cls) -> Path:
        base = Path(settings.STORAGE_DIR).resolve() / "documents"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def save_book_document_file(
        cls,
        book_id: str,
        document_type: str,
        version: int,
        file_bytes: bytes,
    ) -> Tuple[str, int, str]:
        """
        Securely save generated publishing PDF to private disk storage.
        Returns: (storage_key, file_size_bytes, sha256_hash)
        """
        # Document ceiling: 650 MB
        if len(file_bytes) > 650 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="PDF document exceeds 650MB maximum ceiling.",
            )

        sha256 = calculate_sha256(file_bytes)
        doc_type_clean = document_type.lower()
        random_suffix = uuid.uuid4().hex[:8]
        relative_path = f"{book_id}/{doc_type_clean}_v{version}_{random_suffix}.pdf"

        base_dir = cls.get_documents_base_dir()
        dest_path = (base_dir / relative_path).resolve()

        if not dest_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid document destination path.",
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        return relative_path, len(file_bytes), sha256

    @classmethod
    def get_document_path(cls, storage_key: str) -> Path:
        """Resolve and verify storage path for an existing PDF document."""
        base_dir = cls.get_documents_base_dir()
        target_path = (base_dir / storage_key).resolve()

        if not target_path.is_relative_to(base_dir) or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found.",
            )

        return target_path

    @classmethod
    def delete_document_file(cls, storage_key: Optional[str]) -> bool:
        """Safely delete document PDF from disk if it exists."""
        if not storage_key:
            return False
        try:
            base_dir = cls.get_documents_base_dir()
            target_path = (base_dir / storage_key).resolve()
            if target_path.is_relative_to(base_dir) and target_path.is_file():
                target_path.unlink()
                return True
        except Exception:
            pass
        return False

    # -------------------------------------------------------------------------
    # KDP Export Package Storage
    # -------------------------------------------------------------------------
    @classmethod
    def get_exports_base_dir(cls) -> Path:
        base = Path(settings.STORAGE_DIR).resolve() / "exports"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def save_export_package_file(
        cls,
        book_id: str,
        version: int,
        zip_bytes: bytes,
    ) -> Tuple[str, int, str]:
        """
        Securely save generated publishing ZIP package to private disk storage.
        Returns: (storage_key, file_size_bytes, sha256_hash)
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", book_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book identifier for export storage.",
            )
        sha256 = calculate_sha256(zip_bytes)
        random_suffix = uuid.uuid4().hex[:8]
        relative_path = f"{book_id}/kdp_package_v{version}_{random_suffix}.zip"

        base_dir = cls.get_exports_base_dir()
        dest_path = (base_dir / relative_path).resolve()

        if not dest_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid export package path.",
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(zip_bytes)

        return relative_path, len(zip_bytes), sha256

    @classmethod
    def save_export_package_file_from_path(
        cls,
        book_id: str,
        version: int,
        source_path: Path,
    ) -> Tuple[str, int, str]:
        """Atomically move a completed private ZIP file into book-scoped export storage."""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", book_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid book identifier for export storage.",
            )
        base_dir = cls.get_exports_base_dir()
        source = source_path.resolve()
        if not source.is_relative_to(base_dir) or not source.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export temporary file is outside private storage.",
            )

        destination_dir = (base_dir / book_id).resolve()
        if not destination_dir.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid export destination path.",
            )
        destination_dir.mkdir(parents=True, exist_ok=True)
        relative_path = f"{book_id}/kdp_package_v{version}_{uuid.uuid4().hex[:8]}.zip"
        destination = (base_dir / relative_path).resolve()
        if not destination.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid export destination path.",
            )

        digest = hashlib.sha256()
        file_size = 0
        with source.open("rb") as source_file:
            while True:
                chunk = source_file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                file_size += len(chunk)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Generated export package is empty.",
            )

        os.replace(source, destination)
        return relative_path, file_size, digest.hexdigest()

    @classmethod
    def get_export_package_path(cls, storage_key: str) -> Path:
        """Resolve and verify storage path for an existing export ZIP package."""
        base_dir = cls.get_exports_base_dir()
        target_path = (base_dir / storage_key).resolve()

        if not target_path.is_relative_to(base_dir) or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export package file not found.",
            )

        return target_path

    @classmethod
    def delete_export_package_file(cls, storage_key: Optional[str]) -> bool:
        """Safely delete export ZIP from disk if it exists."""
        if not storage_key:
            return False
        base_dir = cls.get_exports_base_dir()
        target_path = (base_dir / storage_key).resolve()
        if not target_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid export package storage path.",
            )
        if not target_path.is_file():
            return False
        target_path.unlink()
        return True

    # -------------------------------------------------------------------------
    # Sales Reports Storage
    # -------------------------------------------------------------------------
    @classmethod
    def get_sales_imports_base_dir(cls) -> Path:
        base = Path(settings.STORAGE_DIR).resolve() / "imports" / "sales"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def save_sales_import_file(
        cls,
        owner_id: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> Tuple[str, int, str, str]:
        """
        Securely save uploaded sales report file (CSV/XLSX) to private disk storage.
        Sanitizes filename and prevents directory traversal.
        Returns: (storage_key, file_size_bytes, sha256_hash, sanitized_filename)
        """
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid owner identifier for sales report storage.",
            )

        original_name = Path(original_filename).name
        suffix = re.sub(r"[^a-zA-Z0-9.]", "", Path(original_name).suffix)[:10]
        stem = re.sub(r"[^a-zA-Z0-9_-]", "_", Path(original_name).stem)[:100]
        safe_name = f"{stem or 'kdp_sales_report'}{suffix}"

        sha256 = calculate_sha256(file_bytes)
        random_suffix = uuid.uuid4().hex[:8]
        relative_path = f"{owner_id}/{random_suffix}_{safe_name}"

        base_dir = cls.get_sales_imports_base_dir()
        dest_path = (base_dir / relative_path).resolve()

        if not dest_path.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Invalid sales import storage path.",
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = dest_path.with_name(f".{uuid.uuid4().hex}.tmp")
        try:
            with open(temp_path, "xb") as report_file:
                report_file.write(file_bytes)
            os.replace(temp_path, dest_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

        return relative_path, len(file_bytes), sha256, safe_name

    @classmethod
    def get_sales_import_path(cls, storage_key: str) -> Path:
        """Resolve and verify storage path for an existing sales report file."""
        base_dir = cls.get_sales_imports_base_dir()
        target_path = (base_dir / storage_key).resolve()

        if not target_path.is_relative_to(base_dir) or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales report file not found.",
            )

        return target_path
