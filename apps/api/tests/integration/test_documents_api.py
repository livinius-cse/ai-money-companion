import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import get_password_hash, generate_csrf_token


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


def test_interior_generation_and_versioning(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    # 1. Create book
    b_res = client.post(
        "/api/v1/books",
        json={"title": "M4 Architecture Guide", "topic": "Publishing Systems", "trim_size": "6x9"},
        headers=headers,
    )
    assert b_res.status_code == 201
    book_id = b_res.json()["id"]

    # 2. Create chapter
    c_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Engine Design", "content": "## Architectural Overview\n\nModular design ensures system resiliency."},
        headers=headers,
    )
    assert c_res.status_code == 201

    # 3. Generate Interior PDF v1
    gen_res1 = client.post(
        f"/api/v1/books/{book_id}/documents/interior/generate",
        json={"include_toc": True, "font_choice": "serif"},
        headers=headers,
    )
    assert gen_res1.status_code == 201
    doc1 = gen_res1.json()
    assert doc1["document_type"] == "INTERIOR"
    assert doc1["version"] == 1
    assert doc1["status"] == "GENERATED"
    assert doc1["page_count"] % 2 == 0  # Even page count physical guarantee

    # 4. Generate Interior PDF v2 (version history maintained)
    gen_res2 = client.post(
        f"/api/v1/books/{book_id}/documents/interior/generate",
        json={"include_toc": False, "font_choice": "sans"},
        headers=headers,
    )
    assert gen_res2.status_code == 201
    doc2 = gen_res2.json()
    assert doc2["version"] == 2

    # 5. List documents
    list_res = client.get(f"/api/v1/books/{book_id}/documents", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 2


def test_cover_generation_and_calculator(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    b_res = client.post(
        "/api/v1/books",
        json={"title": "Cover Engine Handbook", "topic": "Publishing", "trim_size": "6x9", "print_format": "paperback"},
        headers=headers,
    )
    book_id = b_res.json()["id"]

    # Calculator endpoint before interior is compiled (provisional)
    calc_res = client.get(f"/api/v1/books/{book_id}/documents/cover-calculator", headers=headers)
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["format"] == "paperback"
    assert calc_data["full_cover_width_inches"] > 12.0
    assert calc_data["full_cover_height_inches"] == 9.25
    assert calc_data["is_provisional"] is True

    # Attempting to generate cover without an interior document must be rejected (400 Bad Request)
    cov_fail_res = client.post(
        f"/api/v1/books/{book_id}/documents/cover/generate",
        json={
            "custom_front_title": "Cover Engine Handbook",
            "custom_author_name": "Senior Architect",
            "back_cover_description": "Detailed breakdown of KDP cover calculations.",
            "primary_color": "#0f172a",
            "include_spine_text": True,
        },
        headers=headers,
    )
    assert cov_fail_res.status_code == 400
    assert "without a compiled interior PDF" in cov_fail_res.json()["detail"]

    # Now create enough chapters to compile a valid 24-page KDP interior
    # Title(1) + Copyright(2) + 22 chapters = 24 pages
    for i in range(1, 23):
        client.post(
            f"/api/v1/books/{book_id}/chapters",
            json={"chapter_number": i, "title": f"Chapter {i}", "content": f"Content for publishing chapter {i}."},
            headers=headers,
        )

    int_gen_res = client.post(
        f"/api/v1/books/{book_id}/documents/interior/generate",
        json={"include_toc": False, "include_dedication": False},
        headers=headers,
    )
    assert int_gen_res.status_code == 201
    int_doc = int_gen_res.json()
    assert int_doc["page_count"] >= 24

    # Calculator endpoint now reflects authoritative compiled interior
    calc_auth_res = client.get(f"/api/v1/books/{book_id}/documents/cover-calculator", headers=headers)
    assert calc_auth_res.status_code == 200
    calc_auth = calc_auth_res.json()
    assert calc_auth["is_provisional"] is False
    assert calc_auth["is_kdp_compliant_page_count"] is True
    assert calc_auth["interior_page_count"] == int_doc["page_count"]

    # Now generate Cover PDF with verified 24+ page interior
    cov_res = client.post(
        f"/api/v1/books/{book_id}/documents/cover/generate",
        json={
            "custom_front_title": "Cover Engine Handbook",
            "custom_author_name": "Senior Architect",
            "back_cover_description": "Detailed breakdown of KDP cover calculations.",
            "primary_color": "#0f172a",
            "include_spine_text": True,
        },
        headers=headers,
    )
    assert cov_res.status_code == 201
    doc = cov_res.json()
    assert doc["document_type"] == "COVER"
    assert doc["page_count"] == 1
    assert doc["status"] == "GENERATED"


def test_pdf_http_range_streaming_and_download(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    b_res = client.post("/api/v1/books", json={"title": "Streaming Test", "topic": "Tech"}, headers=headers)
    book_id = b_res.json()["id"]

    client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Intro", "content": "Testing streaming bytes."},
        headers=headers,
    )
    doc_res = client.post(
        f"/api/v1/books/{book_id}/documents/interior/generate",
        json={"include_toc": True},
        headers=headers,
    )
    doc_id = doc_res.json()["id"]
    total_size = doc_res.json()["file_size_bytes"]

    # 1. Full GET (200 OK)
    full_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=headers)
    assert full_res.status_code == 200
    assert full_res.headers["Accept-Ranges"] == "bytes"
    assert len(full_res.content) == total_size

    # 2. Single Byte-Range GET (206 Partial Content)
    range_headers = dict(headers)
    range_headers["Range"] = "bytes=0-99"
    part_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=range_headers)
    assert part_res.status_code == 206
    assert part_res.headers["Content-Range"] == f"bytes 0-99/{total_size}"
    assert len(part_res.content) == 100

    # 3. Invalid Byte-Range (416 Range Not Satisfiable)
    invalid_headers = dict(headers)
    invalid_headers["Range"] = f"bytes={total_size + 100}-{total_size + 200}"
    bad_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=invalid_headers)
    assert bad_res.status_code == 416
    assert f"bytes */{total_size}" in bad_res.headers["Content-Range"]

    # 4. HEAD request support (headers only, zero content body)
    head_res = client.head(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=headers)
    assert head_res.status_code == 200
    assert len(head_res.content) == 0
    assert head_res.headers["Content-Length"] == str(total_size)
    assert head_res.headers["Accept-Ranges"] == "bytes"
    assert "private" in head_res.headers["Cache-Control"]

    # 5. Suffix byte ranges
    suffix_headers = dict(headers)
    suffix_headers["Range"] = "bytes=100-"
    suf_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=suffix_headers)
    assert suf_res.status_code == 206
    assert len(suf_res.content) == total_size - 100

    # 6. Download endpoint with RFC 5987 content-disposition
    dl_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert "attachment" in dl_res.headers["Content-Disposition"]
    assert "filename*=" in dl_res.headers["Content-Disposition"]
    assert len(dl_res.content) == total_size


def test_document_ownership_idor(client: TestClient, test_user: User, db_session: Session):
    user_b = User(
        email="user_b_doc@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="User B",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    headers_a = get_auth_headers(client, test_user)
    b_res = client.post("/api/v1/books", json={"title": "User A Private", "topic": "Secret"}, headers=headers_a)
    book_id = b_res.json()["id"]

    client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Private Chapter", "content": "Secret text."},
        headers=headers_a,
    )
    doc_res = client.post(
        f"/api/v1/books/{book_id}/documents/interior/generate",
        json={"include_toc": True},
        headers=headers_a,
    )
    doc_id = doc_res.json()["id"]

    # User B attempts to access User A's document -> 404
    client.cookies.clear()
    headers_b = get_auth_headers(client, user_b)

    get_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}", headers=headers_b)
    assert get_res.status_code == 404

    prev_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/preview", headers=headers_b)
    assert prev_res.status_code == 404

    dl_res = client.get(f"/api/v1/books/{book_id}/documents/{doc_id}/download", headers=headers_b)
    assert dl_res.status_code == 404


def test_quality_audit_endpoint(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    b_res = client.post("/api/v1/books", json={"title": "Quality Audit Book", "topic": "Finance"}, headers=headers)
    book_id = b_res.json()["id"]

    client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={
            "chapter_number": 1,
            "title": "Cash Flow Strategy",
            "content": "The system routes capital into predetermined accounts. Liquidity management prevents emotional trading.",
        },
        headers=headers,
    )

    q_res = client.get(f"/api/v1/books/{book_id}/quality", headers=headers)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["readability"]["is_supported"] is True
    assert "summary" in q_data
    assert "is_preflight_ready" in q_data["summary"]


def test_hardcover_cover_generation_restricted(client: TestClient, test_user: User):
    """Verify automated hardcover full-jacket generation is strictly rejected with 400."""
    headers = get_auth_headers(client, test_user)

    b_res = client.post(
        "/api/v1/books",
        json={"title": "Hardcover Book", "topic": "Tech", "trim_size": "6x9", "print_format": "hardcover"},
        headers=headers,
    )
    hc_id = b_res.json()["id"]

    # Calculator marks as restricted
    calc_res = client.get(f"/api/v1/books/{hc_id}/documents/cover-calculator", headers=headers)
    assert calc_res.status_code == 200
    assert calc_res.json()["is_supported"] is False
    assert "restricted" in calc_res.json()["restriction_reason"].lower()

    # Generate attempt is rejected with 400 Bad Request
    cov_res = client.post(
        f"/api/v1/books/{hc_id}/documents/cover/generate",
        json={"primary_color": "#0f172a"},
        headers=headers,
    )
    assert cov_res.status_code == 400
    assert "restricted" in cov_res.json()["detail"].lower()
    assert "template" in cov_res.json()["detail"].lower()


def test_document_endpoint_path_traversal_rejected(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)
    b_res = client.post("/api/v1/books", json={"title": "Traversal Test", "topic": "Security"}, headers=headers)
    book_id = b_res.json()["id"]

    res = client.get(f"/api/v1/books/{book_id}/documents/../../etc/passwd", headers=headers)
    assert res.status_code in (404, 400, 422)
