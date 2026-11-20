import io
import unicodedata
import pytest
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.models.user import User
from app.services.hasher import (
    CryptographicHasherService,
    nfc_normalize,
    canonical_json_bytes,
    calculate_sha256_hex,
)
from app.core.storage import LocalAssetStorage


def test_nfc_normalization_and_canonical_json():
    # Decomposed: 'e' + combining acute accent (\u0065\u0301)
    # Composed: 'é' (\u00e9)
    decomposed = "Cafe\u0301"
    composed = "Caf\u00e9"
    assert decomposed != composed
    assert nfc_normalize(decomposed) == nfc_normalize(composed)

    data1 = {"b": 2, "a": decomposed}
    data2 = {"a": composed, "b": 2}
    bytes1 = canonical_json_bytes(data1)
    bytes2 = canonical_json_bytes(data2)
    assert bytes1 == bytes2
    assert calculate_sha256_hex(bytes1) == calculate_sha256_hex(bytes2)


def test_hasher_determinism(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Deterministic Wealth Blueprint",
        subtitle="Step by Step Guide",
        topic="Personal Finance",
        book_concept="Practical wealth building",
        target_audience="Young Adults",
        target_reader_profile="Working professionals",
        book_type="non_fiction",
        print_format="paperback",
        marketplace="amazon_com",
        trim_size="6x9",
        paper_type="white_bw",
        target_page_count=100,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    ch1 = Chapter(
        book_id=book.id,
        owner_id=test_user.id,
        chapter_number=1,
        chapter_type="chapter",
        title="Chapter 1: Foundations",
        content="This is the complete text of chapter 1.",
        allocated_pages=10,
    )
    db_session.add(ch1)
    db_session.commit()

    # Compute twice
    hash1 = CryptographicHasherService.compute_manuscript_hash(book, [ch1], [])
    hash2 = CryptographicHasherService.compute_manuscript_hash(book, [ch1], [])
    assert hash1 == hash2
    assert len(hash1) == 64

    meta_hash1 = CryptographicHasherService.compute_metadata_hash(book)
    meta_hash2 = CryptographicHasherService.compute_metadata_hash(book)
    assert meta_hash1 == meta_hash2
    assert len(meta_hash1) == 64


def test_individual_component_changes_alter_hash(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Base Title",
        topic="Finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()

    ch1 = Chapter(
        book_id=book.id,
        owner_id=test_user.id,
        chapter_number=1,
        title="Intro",
        content="Initial content",
    )
    db_session.add(ch1)
    db_session.commit()

    initial_ms_hash = CryptographicHasherService.compute_manuscript_hash(book, [ch1], [])
    initial_meta_hash = CryptographicHasherService.compute_metadata_hash(book)

    # 1. Modify manuscript content -> manuscript_hash changes, metadata_hash does NOT change
    ch1_mod = Chapter(
        book_id=book.id,
        owner_id=test_user.id,
        chapter_number=1,
        title="Intro",
        content="Modified content with updates",
    )
    new_ms_hash = CryptographicHasherService.compute_manuscript_hash(book, [ch1_mod], [])
    assert new_ms_hash != initial_ms_hash
    assert CryptographicHasherService.compute_metadata_hash(book) == initial_meta_hash

    # 2. Modify title -> metadata_hash changes, manuscript_hash does NOT change
    book.title = "Modified Title"
    new_meta_hash = CryptographicHasherService.compute_metadata_hash(book)
    assert new_meta_hash != initial_meta_hash
    assert CryptographicHasherService.compute_manuscript_hash(book, [ch1], []) == initial_ms_hash


def test_composite_hash_changes_with_any_component(db_session: Session, test_user: User):
    book_id = "test-book-id"
    h_ms1 = "1111111111111111111111111111111111111111111111111111111111111111"
    h_meta1 = "2222222222222222222222222222222222222222222222222222222222222222"
    h_int1 = "3333333333333333333333333333333333333333333333333333333333333333"
    h_cov1 = "4444444444444444444444444444444444444444444444444444444444444444"

    composite_base = CryptographicHasherService.compute_composite_hash(
        book_id, h_ms1, h_meta1, h_int1, h_cov1
    )

    # Change manuscript hash
    c_ms = CryptographicHasherService.compute_composite_hash(
        book_id, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", h_meta1, h_int1, h_cov1
    )
    assert c_ms != composite_base

    # Change metadata hash
    c_meta = CryptographicHasherService.compute_composite_hash(
        book_id, h_ms1, "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", h_int1, h_cov1
    )
    assert c_meta != composite_base

    # Change interior hash
    c_int = CryptographicHasherService.compute_composite_hash(
        book_id, h_ms1, h_meta1, "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc", h_cov1
    )
    assert c_int != composite_base

    # Change cover hash
    c_cov = CryptographicHasherService.compute_composite_hash(
        book_id, h_ms1, h_meta1, h_int1, "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    )
    assert c_cov != composite_base


def test_stored_pdf_bytes_tamper_detection(db_session: Session, test_user: User, tmp_path):
    book = Book(
        owner_id=test_user.id,
        title="Tamper Test Book",
        topic="Finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    # Save a real dummy document
    dummy_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    storage_key, size_bytes, original_sha = LocalAssetStorage.save_book_document_file(
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        file_bytes=dummy_pdf_bytes,
    )

    doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        storage_key=storage_key,
        file_size_bytes=size_bytes,
        sha256_hash=original_sha,
        width_pt=432.0,
        height_pt=648.0,
        trim_size="6x9",
    )
    db_session.add(doc)
    db_session.commit()

    # 1. Untampered check
    sha, raw, err = CryptographicHasherService.compute_document_bytes_hash(doc)
    assert err is None
    assert sha == original_sha
    assert raw == dummy_pdf_bytes

    # 2. Tamper file on disk directly
    disk_path = LocalAssetStorage.get_document_path(storage_key)
    with open(disk_path, "wb") as f:
        f.write(b"%PDF-1.4\nTAMPERED_BYTES\n%%EOF\n")

    # 3. Verify tamper is flagged as integrity violation
    sha_tampered, raw_tampered, err_tampered = CryptographicHasherService.compute_document_bytes_hash(doc)
    assert err_tampered is not None
    assert "recorded" in err_tampered
    assert sha_tampered is None


def test_approved_illustration_hash_uses_actual_stored_bytes(db_session: Session, test_user: User):
    book = Book(owner_id=test_user.id, title="Illustrated Book", topic="Finance")
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    key, size, digest = LocalAssetStorage.save_illustration_asset(
        book.id,
        "illustration-test",
        image_bytes,
        "image/png",
    )
    illustration = Illustration(
        book_id=book.id,
        owner_id=test_user.id,
        prompt="A simple test image",
        status="APPROVED_FINAL",
        storage_key=key,
        file_size_bytes=size,
        sha256_hash=digest,
    )
    db_session.add(illustration)
    db_session.commit()

    verified = CryptographicHasherService.compute_all_hashes(db_session, book)
    assert verified["manuscript_hash"] is not None
    assert verified["illustration_errors"] == []

    asset_path = LocalAssetStorage.get_asset_path(key)
    asset_path.write_bytes(image_bytes + b"tampered")
    tampered = CryptographicHasherService.compute_all_hashes(db_session, book)
    assert tampered["manuscript_hash"] is None
    assert tampered["illustration_errors"]
