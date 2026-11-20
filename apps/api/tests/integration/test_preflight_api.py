import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select
from reportlab.pdfgen import canvas

from app.core.security import generate_csrf_token, get_password_hash
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.book_document import BookDocument
from app.models.ai_disclosure import AIDisclosureAttestation
from app.models.approval import BookApprovalSnapshot
from app.core.storage import LocalAssetStorage
from app.services.cover_calculation import CoverCalculationService


def get_auth_headers(client: TestClient, user: User) -> dict:
    login_csrf = generate_csrf_token(identity="anonymous")
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "StrongPassword123!"},
        headers={"X-CSRF-Token": login_csrf, "Origin": "http://localhost:3000"},
    )
    assert login_res.status_code == 200
    user_csrf = login_res.cookies["csrf_token"]
    return {
        "X-CSRF-Token": user_csrf,
        "Origin": "http://localhost:3000",
    }


def create_blank_pdf(pages: int, width_pt: float, height_pt: float) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width_pt, height_pt))
    for p in range(pages):
        c.drawString(72, height_pt - 72, f"Page {p + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(
        email="other_publisher@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="Other Publisher",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def compliant_book(db_session: Session, test_user: User) -> Book:
    book = Book(
        owner_id=test_user.id,
        title="Automated Cash Systems",
        topic="Personal Finance Management and Index Investing",
        book_concept="Tactical system for index funds and wealth preservation.",
        target_audience="General Readers",
        print_format="paperback",
        marketplace="amazon_com",
        trim_size="6x9",
        paper_type="white_bw",
        target_page_count=24,
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)

    # 24 chapters
    for i in range(1, 25):
        ch = Chapter(
            book_id=book.id,
            owner_id=test_user.id,
            chapter_number=i,
            title=f"Wealth Strategy {i}",
            content=f"Tactical protocol for chapter {i}. Managing capital preservation and asset allocation.",
            allocated_pages=1,
            word_count=50,
            draft_status="COMPLETED",
        )
        db_session.add(ch)

    # AI disclosure
    disclosure = AIDisclosureAttestation(
        user_id=test_user.id,
        disclosure_version="1.0",
        text_creation_method="ai_assisted",
        text_tools_used=["Gemini"],
        image_creation_method="none",
        image_tools_used=[],
        translation_creation_method="none",
        translation_tools_used=[],
        kdp_submission_declaration="AI used for drafting with full human author oversight.",
        author_reviewed=True,
        author_attested_at=datetime.now(timezone.utc),
    )
    db_session.add(disclosure)

    # Interior PDF (24 pages, 432x648 pt)
    int_bytes = create_blank_pdf(pages=24, width_pt=432.0, height_pt=648.0)
    int_key, int_size, int_sha = LocalAssetStorage.save_book_document_file(book.id, "INTERIOR", 1, int_bytes)
    int_doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="INTERIOR",
        version=1,
        storage_key=int_key,
        file_size_bytes=int_size,
        sha256_hash=int_sha,
        page_count=24,
        width_pt=432.0,
        height_pt=648.0,
        trim_size="6x9",
        status="GENERATED",
    )
    db_session.add(int_doc)

    # Cover PDF (1 page, calculated full-jacket)
    calc = CoverCalculationService.calculate_full_jacket_cover(
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
        interior_page_count=24,
    )
    cov_bytes = create_blank_pdf(pages=1, width_pt=calc.full_cover_width_pt, height_pt=calc.full_cover_height_pt)
    cov_key, cov_size, cov_sha = LocalAssetStorage.save_book_document_file(book.id, "COVER", 1, cov_bytes)
    cov_doc = BookDocument(
        owner_id=test_user.id,
        book_id=book.id,
        document_type="COVER",
        version=1,
        storage_key=cov_key,
        file_size_bytes=cov_size,
        sha256_hash=cov_sha,
        page_count=1,
        width_pt=calc.full_cover_width_pt,
        height_pt=calc.full_cover_height_pt,
        trim_size="6x9",
        status="GENERATED",
    )
    db_session.add(cov_doc)
    db_session.commit()
    return book


def test_preflight_unauthenticated_and_csrf(client: TestClient, compliant_book: Book):
    # 1. Unauthenticated GET returns 401
    res1 = client.get(f"/api/v1/books/{compliant_book.id}/preflight/report")
    assert res1.status_code == 401

    # 2. POST without CSRF returns 403
    res2 = client.post(f"/api/v1/books/{compliant_book.id}/preflight/run")
    assert res2.status_code == 403


def test_preflight_cross_owner_isolation(client: TestClient, other_user: User, compliant_book: Book):
    headers = get_auth_headers(client, other_user)
    # other_user tries to view compliant_book owned by test_user
    res = client.get(f"/api/v1/books/{compliant_book.id}/preflight/report", headers=headers)
    assert res.status_code == 404


def test_no_approval_on_get(client: TestClient, test_user: User, compliant_book: Book):
    headers = get_auth_headers(client, test_user)
    # Attempting approval via GET request returns 405 Method Not Allowed
    res = client.get(f"/api/v1/books/{compliant_book.id}/preflight/approve", headers=headers)
    assert res.status_code == 405


def test_approve_rejected_when_blocking_qa(client: TestClient, test_user: User, db_session: Session):
    headers = get_auth_headers(client, test_user)
    # Book with no interior or cover documents
    bad_book = Book(
        owner_id=test_user.id,
        title="Unfinished Book",
        topic="Finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(bad_book)
    db_session.commit()

    payload = {"attestation": "I explicitly approve this book despite blocking issues."}
    res = client.post(f"/api/v1/books/{bad_book.id}/preflight/approve", json=payload, headers=headers)
    assert res.status_code == 400
    assert "blocking QA failures" in res.json()["detail"]["message"]


def test_successful_approval_and_snapshot_lifecycle(
    client: TestClient, test_user: User, compliant_book: Book, db_session: Session
):
    headers = get_auth_headers(client, test_user)

    # 1. Run QA via API
    qa_res = client.post(f"/api/v1/books/{compliant_book.id}/preflight/run", headers=headers)
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert qa_data["is_ready_for_approval"] is True
    assert qa_data["blocking_count"] == 0

    # 2. Initial approval check: no active approval yet
    status_res1 = client.get(f"/api/v1/books/{compliant_book.id}/preflight/approval", headers=headers)
    assert status_res1.status_code == 200
    assert status_res1.json()["is_valid"] is False

    # 3. Explicit owner sign-off
    attestation_text = "I have thoroughly reviewed the manuscript and manufacturing specs and confirm publication readiness."
    approve_res = client.post(
        f"/api/v1/books/{compliant_book.id}/preflight/approve",
        json={"attestation": attestation_text},
        headers=headers,
    )
    assert approve_res.status_code == 201
    snapshot = approve_res.json()
    assert snapshot["status"] == "ACTIVE"
    assert snapshot["snapshot_version"] == 1
    assert snapshot["composite_hash"] is not None
    assert snapshot["approval_attestation"] == attestation_text

    # 4. Verify book status transitioned to APPROVED in DB
    db_session.expire_all()
    b = db_session.scalar(select(Book).where(Book.id == compliant_book.id))
    assert b.status == "APPROVED"

    # 5. Check active approval via API
    status_res2 = client.get(f"/api/v1/books/{compliant_book.id}/preflight/approval", headers=headers)
    assert status_res2.status_code == 200
    assert status_res2.json()["is_valid"] is True
    assert status_res2.json()["hash_match"] is True

    # 6. Mutation invalidation: modify chapter 1 content
    ch1 = db_session.scalar(
        select(Chapter).where(Chapter.book_id == compliant_book.id, Chapter.chapter_number == 1)
    )
    edit_res = client.put(
        f"/api/v1/books/{compliant_book.id}/chapters/{ch1.id}",
        json={"content": "Completely new modified chapter content that alters the manuscript hash."},
        headers=headers,
    )
    assert edit_res.status_code == 200

    # 7. Check approval status after mutation: automatically invalidated!
    status_res3 = client.get(f"/api/v1/books/{compliant_book.id}/preflight/approval", headers=headers)
    assert status_res3.status_code == 200
    assert status_res3.json()["is_valid"] is False

    # 8. Check history: preserved with invalidation reason
    hist_res = client.get(f"/api/v1/books/{compliant_book.id}/preflight/approval/history", headers=headers)
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["total"] >= 1
    latest_hist = hist["items"][0]
    assert latest_hist["status"] == "INVALIDATED"
    assert "edited" in latest_hist["invalidation_reason"].lower()
