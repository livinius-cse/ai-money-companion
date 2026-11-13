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


def test_chapters_crud_and_reorder(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    # 1. Create a book
    book_res = client.post(
        "/api/v1/books",
        json={"title": "Test Book for Chapters", "topic": "Personal Finance"},
        headers=headers,
    )
    assert book_res.status_code == 201
    book_id = book_res.json()["id"]

    # 2. Create chapters
    chap1_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Chapter 1: Foundations", "allocated_pages": 12},
        headers=headers,
    )
    assert chap1_res.status_code == 201
    chap1_id = chap1_res.json()["id"]

    chap2_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 2, "title": "Chapter 2: Cash Flow", "allocated_pages": 14},
        headers=headers,
    )
    assert chap2_res.status_code == 201
    chap2_id = chap2_res.json()["id"]

    # 3. List chapters
    list_res = client.get(f"/api/v1/books/{book_id}/chapters", headers=headers)
    assert list_res.status_code == 200
    chaps = list_res.json()
    assert len(chaps) == 2
    assert chaps[0]["id"] == chap1_id
    assert chaps[1]["id"] == chap2_id

    # 4. Update chapter content
    md_content = "# Chapter 1\n\nThis is a practical chapter with exactly sixteen words in this sentence."
    update_res = client.put(
        f"/api/v1/books/{book_id}/chapters/{chap1_id}",
        json={"content": md_content, "draft_status": "DRAFT"},
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["word_count"] > 10
    assert updated_data["estimated_reading_minutes"] >= 1
    assert updated_data["draft_status"] == "DRAFT"

    # 5. Reorder chapters (swap order)
    reorder_payload = {
        "reordered_chapters": [
            {"chapter_id": chap1_id, "chapter_number": 2},
            {"chapter_id": chap2_id, "chapter_number": 1},
        ]
    }
    reorder_res = client.post(
        f"/api/v1/books/{book_id}/chapters/reorder",
        json=reorder_payload,
        headers=headers,
    )
    assert reorder_res.status_code == 200
    reordered_list = reorder_res.json()
    assert reordered_list[0]["id"] == chap2_id
    assert reordered_list[0]["chapter_number"] == 1
    assert reordered_list[1]["id"] == chap1_id
    assert reordered_list[1]["chapter_number"] == 2

    # 6. Delete chapter
    del_res = client.delete(f"/api/v1/books/{book_id}/chapters/{chap1_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify 404
    get_del = client.get(f"/api/v1/books/{book_id}/chapters/{chap1_id}", headers=headers)
    assert get_del.status_code == 404


def test_ai_draft_chapter_and_safety(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    # 1. Create book and chapter
    book_res = client.post(
        "/api/v1/books",
        json={"title": "The 30-Day Money Reset", "topic": "Personal Finance"},
        headers=headers,
    )
    book_id = book_res.json()["id"]

    chap_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Taking Stock: The Reality Check Audit", "content": "Existing manual notes."},
        headers=headers,
    )
    chap_id = chap_res.json()["id"]

    # 2. Trigger AI draft generation
    draft_res = client.post(
        f"/api/v1/books/{book_id}/chapters/{chap_id}/draft",
        json={"target_words": 1500},
        headers=headers,
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert draft_data["is_draft"] is True
    assert draft_data["author_reviewed"] is False
    assert len(draft_data["markdown_content"]) > 100

    # 3. SAFETY CHECK: The database content must NOT be overwritten automatically!
    check_chap = client.get(f"/api/v1/books/{book_id}/chapters/{chap_id}", headers=headers).json()
    assert check_chap["content"] == "Existing manual notes."

    # 4. User reviews and explicitly saves the draft
    save_res = client.put(
        f"/api/v1/books/{book_id}/chapters/{chap_id}",
        json={"content": draft_data["markdown_content"], "draft_status": "DRAFT"},
        headers=headers,
    )
    assert save_res.status_code == 200
    assert save_res.json()["content"] == draft_data["markdown_content"]


def test_ai_section_expand_and_regenerate(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    book_res = client.post("/api/v1/books", json={"title": "Systems Guide", "topic": "Productivity"}, headers=headers)
    book_id = book_res.json()["id"]

    chap_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={"chapter_number": 1, "title": "Foundation"},
        headers=headers,
    )
    chap_id = chap_res.json()["id"]

    # Expand section
    exp_res = client.post(
        f"/api/v1/books/{book_id}/chapters/{chap_id}/expand-section",
        json={"section_heading": "Core Protocols", "current_text": "Follow daily steps."},
        headers=headers,
    )
    assert exp_res.status_code == 200
    assert len(exp_res.json()["expanded_markdown"]) > 20

    # Regenerate section
    regen_res = client.post(
        f"/api/v1/books/{book_id}/chapters/{chap_id}/regenerate-section",
        json={"section_heading": "Core Protocols", "current_text": "Follow daily steps."},
        headers=headers,
    )
    assert regen_res.status_code == 200
    assert len(regen_res.json()["regenerated_markdown"]) > 20
