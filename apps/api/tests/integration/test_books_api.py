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


def test_books_crud_lifecycle(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    # 1. Create a book
    payload = {
        "title": "Smart Wealth Systems",
        "subtitle": "A Practical Financial Guide",
        "topic": "Personal Finance and Debt Elimination",
        "book_concept": "Frameworks for automated cash flow allocation.",
        "target_audience": "Young professionals",
        "target_reader_profile": "Mid-career earner looking to optimize investments.",
        "book_type": "non_fiction",
        "print_format": "paperback",
        "marketplace": "amazon_com",
        "trim_size": "6x9",
        "paper_type": "white_bw",
        "target_page_count": 120,
    }
    create_res = client.post("/api/v1/books", json=payload, headers=headers)
    assert create_res.status_code == 201
    book_data = create_res.json()
    book_id = book_data["id"]
    assert book_data["title"] == "Smart Wealth Systems"
    assert book_data["status"] == "DRAFT"
    assert book_data["chapter_count"] == 0

    # 2. List books
    list_res = client.get("/api/v1/books", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(b["id"] == book_id for b in list_data["items"])

    # 3. Get single book
    get_res = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == book_id

    # 4. Update book
    update_res = client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "Smart Wealth Systems (Revised)", "status": "IN_PROGRESS"},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Smart Wealth Systems (Revised)"
    assert update_res.json()["status"] == "IN_PROGRESS"

    # 5. Delete book
    del_res = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    get_after_del = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_after_del.status_code == 404


def test_books_ownership_isolation_and_idor(client: TestClient, test_user: User, db_session: Session):
    # Setup User B
    user_b = User(
        email="user_b@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="User B",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    # User A creates a book
    headers_a = get_auth_headers(client, test_user)
    create_res = client.post(
        "/api/v1/books",
        json={"title": "User A Private Book", "topic": "Top Secret Strategies"},
        headers=headers_a,
    )
    assert create_res.status_code == 201
    book_id_a = create_res.json()["id"]

    # User B logs in (clear User A's session cookies first)
    client.cookies.clear()
    headers_b = get_auth_headers(client, user_b)

    # User B attempts to access User A's book -> MUST return 404
    get_res = client.get(f"/api/v1/books/{book_id_a}", headers=headers_b)
    assert get_res.status_code == 404

    # User B attempts to modify User A's book -> MUST return 404
    put_res = client.put(f"/api/v1/books/{book_id_a}", json={"title": "Hacked"}, headers=headers_b)
    assert put_res.status_code == 404

    # User B attempts to delete User A's book -> MUST return 404
    del_res = client.delete(f"/api/v1/books/{book_id_a}", headers=headers_b)
    assert del_res.status_code == 404


def test_book_plan_generation_and_apply(client: TestClient, test_user: User):
    headers = get_auth_headers(client, test_user)

    # 1. Create book
    create_res = client.post(
        "/api/v1/books",
        json={
            "title": "Initial Working Title",
            "topic": "Personal Finance and Debt Snowball",
            "target_page_count": 100,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    # 2. Generate plan using MockAIProvider
    gen_res = client.post(f"/api/v1/books/{book_id}/plan/generate", headers=headers)
    assert gen_res.status_code == 200
    plan_data = gen_res.json()
    assert len(plan_data["chapters"]) >= 3
    assert len(plan_data["title_options"]) >= 1

    # 3. Apply accepted plan
    apply_payload = {
        "selected_title": plan_data["title_options"][0],
        "selected_subtitle": plan_data["subtitle_options"][0],
        "target_reader_avatar": plan_data["target_reader_avatar"],
        "front_matter_pages": plan_data["front_matter_pages"],
        "back_matter_pages": plan_data["back_matter_pages"],
        "chapters": plan_data["chapters"],
    }
    apply_res = client.post(f"/api/v1/books/{book_id}/plan/apply", json=apply_payload, headers=headers)
    assert apply_res.status_code == 200
    updated_book = apply_res.json()
    assert updated_book["title"] == plan_data["title_options"][0]
    assert updated_book["chapter_count"] == len(plan_data["chapters"])
    assert updated_book["total_allocated_pages"] > 0
    assert updated_book["status"] == "PLANNING"
