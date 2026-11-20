import hashlib
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.milestone6 import _verify_export_archive
from app.services.package_exporter import is_safe_zip_path


@pytest.mark.parametrize(
    "filename",
    [
        "",
        "/absolute/path",
        "../outside.txt",
        "nested/../outside.txt",
        "C:/outside.txt",
        "C:\\outside.txt",
        "nested\\file.txt",
        "nested//file.txt",
        "./file.txt",
    ],
)
def test_unsafe_zip_member_paths_are_rejected(filename: str):
    assert not is_safe_zip_path(filename)


def test_safe_zip_member_paths_are_accepted():
    assert is_safe_zip_path("interior.pdf")
    assert is_safe_zip_path("metadata/copy-sheet.txt")


def test_export_archive_manifest_and_member_hashes_are_verified(tmp_path):
    member_name = "interior.pdf"
    member_bytes = b"%PDF-1.7\nverified"
    manifest = {
        "files": {
            member_name: {
                "sha256": hashlib.sha256(member_bytes).hexdigest(),
                "size_bytes": len(member_bytes),
            }
        }
    }
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode("utf-8")
    archive_path = tmp_path / "package.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member_name, member_bytes)
        archive.writestr("manifest.json", manifest_bytes)

    package = SimpleNamespace(
        file_size_bytes=archive_path.stat().st_size,
        sha256_hash=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        manifest_data=manifest,
    )

    _verify_export_archive(archive_path, package)

    package.sha256_hash = "0" * 64
    with pytest.raises(HTTPException) as error:
        _verify_export_archive(archive_path, package)
    assert error.value.status_code == 409
