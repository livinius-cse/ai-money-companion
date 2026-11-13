import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, generate_csrf_token
from app.models.user import User


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


def test_illustrations_crud_and_ai_prompts(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    book_res = client.post("/api/v1/books", json={"title": "Visual Book", "topic": "Finance"}, headers=headers)
    book_id = book_res.json()["id"]

    # 1. Create a prompt
    create_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={
            "prompt": "Line-art debt snowball payoff chart.",
            "description": "Infographic showing progressive debt balance reductions.",
            "style_preset": "modern_clean_vector",
            "status": "PROMPT",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    ill_data = create_res.json()
    assert ill_data["status"] == "PROMPT"
    ill_id = ill_data["id"]

    # 2. List illustrations
    list_res = client.get(f"/api/v1/books/{book_id}/illustrations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. AI prompt generation
    gen_res = client.post(
        f"/api/v1/books/{book_id}/illustrations/generate-prompts",
        json={"target_count": 3, "style_preset": "clean_minimalist_line_art"},
        headers=headers,
    )
    assert gen_res.status_code == 200
    assert len(gen_res.json()["prompts"]) == 3


def test_illustration_upload_asset_retrieval_and_approval(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    book_res = client.post("/api/v1/books", json={"title": "Asset Book", "topic": "Finance"}, headers=headers)
    book_id = book_res.json()["id"]

    # 1. Create placeholder
    create_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={
            "prompt": "Cash flow diagram.",
            "status": "PLACEHOLDER",
        },
        headers=headers,
    )
    ill_id = create_res.json()["id"]

    # 2. Upload valid PNG file
    png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    upload_headers = {
        "X-CSRF-Token": headers["X-CSRF-Token"],
        "Origin": headers["Origin"],
    }
    files = {"file": ("test_diagram.png", io.BytesIO(png_content), "image/png")}
    upload_res = client.post(
        f"/api/v1/books/{book_id}/illustrations/{ill_id}/upload",
        files=files,
        headers=upload_headers,
    )
    assert upload_res.status_code == 200
    uploaded_data = upload_res.json()
    assert uploaded_data["status"] == "GENERATED"
    assert uploaded_data["asset_source"] == "MANUAL_UPLOAD"
    assert uploaded_data["sha256_hash"] is not None
    assert uploaded_data["file_size_bytes"] == len(png_content)

    # 3. Retrieve image asset via authenticated endpoint
    asset_res = client.get(f"/api/v1/books/{book_id}/illustrations/{ill_id}/asset", headers=headers)
    assert asset_res.status_code == 200
    assert asset_res.content == png_content
    assert "image/png" in asset_res.headers.get("content-type", "")
    assert "private" in asset_res.headers.get("cache-control", "")

    # 4. Status transition to APPROVED_FINAL requires human approval
    # Attempt without human_approved -> 400
    fail_approve = client.patch(
        f"/api/v1/books/{book_id}/illustrations/{ill_id}/status",
        json={"status": "APPROVED_FINAL", "human_approved": False},
        headers=headers,
    )
    assert fail_approve.status_code == 400
    assert "human approval" in fail_approve.json()["detail"]

    # Succeeded with human_approved
    success_approve = client.patch(
        f"/api/v1/books/{book_id}/illustrations/{ill_id}/status",
        json={"status": "APPROVED_FINAL", "human_approved": True},
        headers=headers,
    )
    assert success_approve.status_code == 200
    assert success_approve.json()["status"] == "APPROVED_FINAL"

    # 5. Delete illustration
    del_res = client.delete(f"/api/v1/books/{book_id}/illustrations/{ill_id}", headers=headers)
    assert del_res.status_code == 204

    # Asset retrieval after deletion -> 404
    asset_after_del = client.get(f"/api/v1/books/{book_id}/illustrations/{ill_id}/asset", headers=headers)
    assert asset_after_del.status_code == 404


def test_illustration_invalid_upload_rejected(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    book_res = client.post("/api/v1/books", json={"title": "Rejection Book", "topic": "Finance"}, headers=headers)
    book_id = book_res.json()["id"]

    create_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={"prompt": "Test rejection", "status": "PLACEHOLDER"},
        headers=headers,
    )
    ill_id = create_res.json()["id"]

    # Upload fake image file (text content claiming to be png)
    fake_content = b"This is not a real PNG image file."
    files = {"file": ("malicious.png", io.BytesIO(fake_content), "image/png")}
    upload_res = client.post(
        f"/api/v1/books/{book_id}/illustrations/{ill_id}/upload",
        files=files,
        headers={"X-CSRF-Token": headers["X-CSRF-Token"], "Origin": headers["Origin"]},
    )
    assert upload_res.status_code == 400
    assert "Invalid image format" in upload_res.json()["detail"]


def test_illustration_ownership_idor(client: TestClient, test_user: User, db_session: Session):
    user_b = User(
        email="user_b_ill@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="User B",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    headers_a = get_auth_headers(client, test_user)
    book_res = client.post("/api/v1/books", json={"title": "User A Book", "topic": "Finance"}, headers=headers_a)
    book_id = book_res.json()["id"]

    ill_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={"prompt": "User A Secret Diagram"},
        headers=headers_a,
    )
    ill_id = ill_res.json()["id"]

    # User B attempts to access User A's illustration -> 404
    client.cookies.clear()
    headers_b = get_auth_headers(client, user_b)
    get_res = client.get(f"/api/v1/books/{book_id}/illustrations/{ill_id}", headers=headers_b)
    assert get_res.status_code == 404

    del_res = client.delete(f"/api/v1/books/{book_id}/illustrations/{ill_id}", headers=headers_b)
    assert del_res.status_code == 404
