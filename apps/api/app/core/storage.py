import hashlib
import os
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
