import os
import sys
import tempfile
import pytest
from pathlib import Path

from app.core.security_fetcher import (
    SecureAssetURLFetcher,
    SecurityFetchError,
    weasyprint_secure_url_fetcher,
)
from app.core.config import settings

# Valid 1x1 PNG bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
    b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)


def test_reject_arbitrary_file_schemes():
    """Verify arbitrary file:// URIs are unconditionally rejected."""
    bad_urls = [
        "file:///etc/passwd",
        "file:///C:/Windows/win.ini",
        "file:///C:/Users/Administrator/secrets.txt",
        "file://localhost/etc/shadow",
        "FILE:///etc/hosts",
    ]
    for url in bad_urls:
        with pytest.raises(SecurityFetchError) as exc_info:
            SecureAssetURLFetcher.fetch_resource(url)
        assert "prohibited" in str(exc_info.value).lower() or "direct file://" in str(exc_info.value).lower()


def test_reject_remote_http_and_https_ssrf():
    """Verify HTTP and HTTPS requests are blocked to prevent SSRF and data exfiltration."""
    bad_urls = [
        "http://malicious-attacker.com/payload.png",
        "https://169.254.169.254/latest/meta-data/",
        "http://localhost:8000/internal-admin",
        "http://127.0.0.1:22",
        "https://evil.org/styles.css",
    ]
    for url in bad_urls:
        with pytest.raises(SecurityFetchError) as exc_info:
            SecureAssetURLFetcher.fetch_resource(url)
        assert "remote http/https" in str(exc_info.value).lower()


def test_reject_unsupported_and_dangerous_schemes():
    """Verify alternative schemes like ftp, javascript, data, gopher are blocked."""
    bad_urls = [
        "ftp://attacker.com/image.jpg",
        "javascript:alert(1)",
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg==",
        "gopher://evil.com",
        "ldap://evil.com/payload",
    ]
    for url in bad_urls:
        with pytest.raises(SecurityFetchError):
            SecureAssetURLFetcher.fetch_resource(url)


def test_reject_path_traversal_attempts():
    """Verify parent directory traversal patterns (.. / and ..\\) are blocked."""
    traversal_keys = [
        "../../etc/passwd",
        "..\\..\\Windows\\win.ini",
        "....//....//config.py",
        "/etc/shadow",
        "C:\\Windows\\System32\\cmd.exe",
        "sub/../../secret.key",
    ]
    for key in traversal_keys:
        with pytest.raises(SecurityFetchError) as exc_info:
            SecureAssetURLFetcher.validate_and_resolve_asset_path(key)
        assert "traversal" in str(exc_info.value).lower() or "prohibited" in str(exc_info.value).lower() or "escapes" in str(exc_info.value).lower()


def test_reject_non_existent_asset():
    """Verify missing asset keys raise SecurityFetchError without exposing system paths."""
    with pytest.raises(SecurityFetchError) as exc_info:
        SecureAssetURLFetcher.validate_and_resolve_asset_path("non_existent_image_12345.png")
    assert "does not exist" in str(exc_info.value).lower()
    # Confirm no local path disclosure
    assert settings.STORAGE_DIR not in str(exc_info.value)


def test_reject_invalid_magic_bytes_not_image(tmp_path, monkeypatch):
    """Verify non-image content (e.g. bash scripts, HTML, executables) is rejected."""
    # Create an executable script disguised as png
    root = tmp_path / "illustrations"
    root.mkdir(parents=True)
    monkeypatch.setattr(SecureAssetURLFetcher, "get_illustrations_root", classmethod(lambda cls: root))

    fake_asset = root / "fake_exploit.png"
    fake_asset.write_bytes(b"#!/bin/bash\nrm -rf /\necho pwned\n")

    with pytest.raises(SecurityFetchError) as exc_info:
        SecureAssetURLFetcher.fetch_resource(f"asset://fake_exploit.png")
    assert "image format" in str(exc_info.value).lower()


def test_fetch_valid_approved_asset_succeeds(tmp_path, monkeypatch):
    """Verify legitimate PNG asset inside storage root resolves and fetches successfully."""
    root = tmp_path / "illustrations"
    root.mkdir(parents=True)
    monkeypatch.setattr(SecureAssetURLFetcher, "get_illustrations_root", classmethod(lambda cls: root))

    valid_asset = root / "valid_test_illustration.png"
    valid_asset.write_bytes(VALID_PNG_BYTES)

    # Fetch via asset:// scheme
    result = weasyprint_secure_url_fetcher("asset://valid_test_illustration.png")
    assert result["string"] == VALID_PNG_BYTES
    assert result["mime_type"] == "image/png"
    assert result["filename"] == "valid_test_illustration.png"

    # Fetch via direct key
    res2 = SecureAssetURLFetcher.fetch_resource("valid_test_illustration.png")
    assert res2["string"] == VALID_PNG_BYTES
    assert res2["mime_type"] == "image/png"
