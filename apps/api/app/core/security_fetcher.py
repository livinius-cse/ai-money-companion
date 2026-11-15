import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import mimetypes
from urllib.parse import urlparse

from app.core.config import settings

# Permitted MIME types for publication assets
ALLOWED_IMAGE_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

try:
    from weasyprint.urls import URLFetcherResponse as BaseURLFetcherResponse
except (ImportError, OSError):
    BaseURLFetcherResponse = object


class SecureURLFetcherResponse(BaseURLFetcherResponse):
    """
    Dual-compatible URL fetcher response that supports both dictionary access
    (res['string'], res['mime_type']) and WeasyPrint 70+ URLFetcherResponse object protocol.
    """
    def __init__(self, url: str, body: bytes, mime_type: str, filename: str):
        if BaseURLFetcherResponse is not object:
            super().__init__(url=url, body=body, headers={"content-type": mime_type})
        self._dict = {
            "string": body,
            "mime_type": mime_type,
            "filename": filename,
        }

    def __getitem__(self, item):
        return self._dict[item]

    def __contains__(self, item):
        return item in self._dict

    def get(self, item, default=None):
        return self._dict.get(item, default)

    def items(self):
        return self._dict.items()

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()


class SecurityFetchError(Exception):
    """Raised when an asset fetch or resource resolution violates security boundaries."""
    pass


class SecureAssetURLFetcher:
    """
    High-security resource resolver and URL fetcher for publishing rendering engines.

    Security Controls:
    1. Blocks arbitrary file:// access unconditionally.
    2. Blocks remote http:// and https:// access to prevent SSRF and external asset leakage.
    3. Blocks all alternative protocols (ftp://, gopher://, data:, javascript:, etc.).
    4. Enforces strict canonical path resolution against permitted storage roots (no traversal, no symlink escape).
    5. Validates magic bytes / MIME types against allowed image signatures.
    6. Sanitizes exceptions so internal filesystem structures are never exposed.
    """

    @classmethod
    def get_illustrations_root(cls) -> Path:
        """Return canonical illustrations storage directory."""
        root = (Path(settings.STORAGE_DIR).resolve() / "illustrations").resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    @classmethod
    def validate_and_resolve_asset_path(cls, storage_key: str) -> Path:
        """
        Validate storage key and resolve to an absolute path strictly within the illustrations root.
        Rejects path traversal, symlink escapes, and non-existent assets.
        """
        if not storage_key or not isinstance(storage_key, str):
            raise SecurityFetchError("Invalid asset identifier: key must be a non-empty string.")

        # Disallow raw URLs or scheme prefixes
        lower_key = storage_key.strip().lower()
        if lower_key.startswith(("file:", "http:", "https:", "ftp:", "data:", "javascript:")):
            raise SecurityFetchError(f"Access to URI scheme is prohibited: {storage_key[:10]}")

        # Check for traversal patterns
        if ".." in storage_key or "\\" in storage_key or storage_key.startswith("/"):
            # Check for Windows or Unix absolute paths or parent references
            raise SecurityFetchError("Path traversal or absolute path references are strictly prohibited.")

        root = cls.get_illustrations_root()
        target = (root / storage_key).resolve()

        # Strict containment verification
        if not target.is_relative_to(root):
            raise SecurityFetchError("Target asset escapes the permitted storage directory boundary.")

        # Realpath check to prevent symlink traversal
        real_target = Path(os.path.realpath(str(target)))
        real_root = Path(os.path.realpath(str(root)))
        if not real_target.is_relative_to(real_root):
            raise SecurityFetchError("Symlink escape detected: asset resolves outside permitted storage root.")

        if not target.is_file():
            raise SecurityFetchError("Referenced asset file does not exist.")

        return target

    @classmethod
    def fetch_resource(cls, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        WeasyPrint / PDF engine compatible URL fetcher interface.
        Returns a dictionary with keys:
          - 'string': raw bytes
          - 'mime_type': validated MIME type
          - 'filename': safe filename
        """
        if not url or not isinstance(url, str):
            raise SecurityFetchError("Resource URL must be a non-empty string.")

        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()

        # 1. Unconditionally reject network protocols (prevent SSRF)
        if scheme in ("http", "https"):
            raise SecurityFetchError(f"Remote HTTP/HTTPS resource retrieval is prohibited during PDF compilation: {scheme}://...")

        # 2. Unconditionally reject file:// schemes
        if scheme == "file":
            raise SecurityFetchError("Direct file:// URI access is prohibited during PDF compilation.")

        # 3. Reject other schemes
        if scheme and scheme not in ("asset", "app"):
            raise SecurityFetchError(f"Unsupported or prohibited resource scheme: {scheme}")

        # 4. Resolve internal asset key
        # Format: "asset://<storage_key>" or pure key
        if scheme in ("asset", "app"):
            key = parsed.netloc + parsed.path
            # Strip leading slashes
            key = key.lstrip("/")
        else:
            key = url.strip()

        target_path = cls.validate_and_resolve_asset_path(key)

        with open(target_path, "rb") as f:
            data = f.read()

        # Validate magic bytes
        mime_type = cls._detect_safe_mime_type(data)
        if not mime_type:
            raise SecurityFetchError("Asset content does not match permitted image format signatures.")

        return SecureURLFetcherResponse(
            url=url,
            body=data,
            mime_type=mime_type,
            filename=target_path.name,
        )

    @classmethod
    def _detect_safe_mime_type(cls, file_bytes: bytes) -> Optional[str]:
        """Validate binary signatures against allowed image formats."""
        if len(file_bytes) < 12:
            return None
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
            return "image/webp"
        return None


def weasyprint_secure_url_fetcher(url: str, *args, **kwargs) -> Any:
    """
    Drop-in custom URL fetcher for WeasyPrint HTML/CSS compilation pipelines.
    Guarantees strict sandboxing against local file leakage and remote SSRF.
    """
    return SecureAssetURLFetcher.fetch_resource(url)

weasyprint_secure_url_fetcher._fail_on_errors = False
