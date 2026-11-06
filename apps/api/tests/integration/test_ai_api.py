import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import generate_csrf_token
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


# -----------------------------------------------------------------------------
# 1. Public Catalog Specifications Endpoint
# -----------------------------------------------------------------------------
def test_specs_endpoint_public_unauthenticated(client: TestClient):
    """GET /api/v1/ai/specs is public, requires no auth or CSRF, returns versioned specs."""
    response = client.get("/api/v1/ai/specs")
    assert response.status_code == 200
    data = response.json()
    assert data["spec_version"] == "2.3.10"
    assert "paperback_specifications" in data
    assert "hardcover_specification_model" in data
    assert "gutter_margins" in data
    assert len(data["paperback_specifications"]) == 79


# -----------------------------------------------------------------------------
# 2. Book Planning Endpoint (/plan)
# -----------------------------------------------------------------------------
def test_plan_endpoint_unauthenticated_rejected(client: TestClient, anon_csrf_token: str):
    """POST /api/v1/ai/plan with anon CSRF but no auth session returns 401."""
    response = client.post(
        "/api/v1/ai/plan",
        json={"topic": "Personal Finance", "target_audience": "Beginners"},
        headers={"X-CSRF-Token": anon_csrf_token, "Origin": "http://localhost:3000"},
    )
    assert response.status_code == 401


def test_plan_endpoint_csrf_enforced(client: TestClient, test_user: User):
    """POST /api/v1/ai/plan without CSRF header returns 403."""
    # Login to set session cookie
    login_csrf = generate_csrf_token(identity="anonymous")
    client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={"X-CSRF-Token": login_csrf, "Origin": "http://localhost:3000"},
    )
    # Request without X-CSRF-Token header
    response = client.post(
        "/api/v1/ai/plan",
        json={"topic": "Personal Finance", "target_audience": "Beginners"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 403


def test_plan_endpoint_success(client: TestClient, test_user: User):
    """POST /api/v1/ai/plan with valid auth and CSRF returns structured plan envelope."""
    headers = get_auth_headers(client, test_user)
    payload = {
        "topic": "Debt Snowball Guide",
        "target_audience": "Working adults with credit debt",
        "book_type": "NON_FICTION",
        "print_format": "paperback",
        "target_trim_size": "6x9",
        "paper_type": "white_bw",
        "target_pages": 100,
    }
    response = client.post("/api/v1/ai/plan", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "telemetry" in body
    assert body["telemetry"]["requested_provider"] == "mock"
    assert body["telemetry"]["is_mock_generated"] is True
    plan = body["data"]
    assert plan["total_calculated_pages"] == 100
    assert plan["specification_matched"] is True


def test_plan_endpoint_kdp_violation_rfc7807(client: TestClient, test_user: User):
    """POST /api/v1/ai/plan with specification violation returns 400 Problem Details."""
    headers = get_auth_headers(client, test_user)
    # Request with invalid trim/paper combination that will trigger blocking error on validation
    payload = {
        "topic": "Hardcover Color Book",
        "target_audience": "General",
        "print_format": "hardcover",
        "target_trim_size": "6x9",
        "paper_type": "standard_color",  # Prohibited for hardcover
        "target_pages": 100,
    }
    response = client.post("/api/v1/ai/plan", json=payload, headers=headers)
    assert response.status_code == 400
    assert "application/problem+json" in response.headers.get("content-type", "")
    problem = response.json()
    assert problem["status"] == 400
    assert "invalid-plan-parameters" in problem["type"]
    assert "prohibited for hardcover" in problem["detail"].lower()


# -----------------------------------------------------------------------------
# 3. Metadata Generation Endpoint (/metadata)
# -----------------------------------------------------------------------------
def test_metadata_endpoint_success(client: TestClient, test_user: User):
    """POST /api/v1/ai/metadata generates compliant SEO metadata and unconfirmed draft."""
    headers = get_auth_headers(client, test_user)
    payload = {
        "title": "Zero to Invested: The Simple Wealth Playbook",
        "subtitle": "How to Automate Your Savings in 30 Days",
        "topic_summary": "Practical manual for total stock market investing and automated budgeting.",
        "target_audience": "Young professionals aged 25-40",
    }
    response = client.post("/api/v1/ai/metadata", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    metadata = body["data"]
    assert 1 <= len(metadata["keywords"]) <= 7
    assert 1 <= len(metadata["categories"]) <= 3
    assert "<p>" in metadata["description_html"]
    assert metadata["unconfirmed_disclosure_recommendation"]["author_confirmed"] is False


# -----------------------------------------------------------------------------
# 4. AI Disclosure Attestation Endpoints (/disclosure/*)
# -----------------------------------------------------------------------------
def test_disclosure_confirm_and_latest_lifecycle(client: TestClient, test_user: User):
    """Verify confirming AI disclosure persists record and GET /disclosure/latest retrieves it."""
    headers = get_auth_headers(client, test_user)

    # 1. Initial check: GET /disclosure/latest returns 404 before confirmation
    res_before = client.get("/api/v1/ai/disclosure/latest")
    assert res_before.status_code == 404

    # 2. Confirm disclosure: POST /disclosure/confirm
    payload = {
        "text_creation_method": "ai_generated",
        "text_tools_used": ["Claude 3.5 Sonnet"],
        "text_editing_extent": "extensive_editing",
        "image_creation_method": "none",
        "image_tools_used": [],
        "image_editing_extent": None,
        "translation_creation_method": "none",
        "translation_tools_used": [],
        "translation_editing_extent": None,
        "author_confirmed": True,
    }
    res_confirm = client.post("/api/v1/ai/disclosure/confirm", json=payload, headers=headers)
    assert res_confirm.status_code == 201
    created_data = res_confirm.json()
    assert created_data["user_id"] == test_user.id
    assert created_data["author_reviewed"] is True
    assert created_data["author_attested_at"] is not None
    assert "Claude 3.5 Sonnet" in created_data["kdp_submission_declaration"]

    # 3. Retrieve latest: GET /disclosure/latest (safe method, no CSRF header required)
    res_latest = client.get("/api/v1/ai/disclosure/latest")
    assert res_latest.status_code == 200
    latest_data = res_latest.json()
    assert latest_data["id"] == created_data["id"]
    assert latest_data["user_id"] == test_user.id
    assert latest_data["author_reviewed"] is True


def test_disclosure_confirm_unconfirmed_rejected(client: TestClient, test_user: User):
    """POST /disclosure/confirm with author_confirmed=False returns 422."""
    headers = get_auth_headers(client, test_user)
    payload = {
        "text_creation_method": "none",
        "image_creation_method": "none",
        "translation_creation_method": "none",
        "author_confirmed": False,
    }
    res = client.post("/api/v1/ai/disclosure/confirm", json=payload, headers=headers)
    assert res.status_code == 422


# -----------------------------------------------------------------------------
# 5. KDP Spec Validation Endpoints (/validate/*)
# -----------------------------------------------------------------------------
def test_validate_print_specs_endpoint(client: TestClient, test_user: User):
    """POST /api/v1/ai/validate/print-specs validates against verified KDP matrix."""
    headers = get_auth_headers(client, test_user)

    # Valid spec
    valid_payload = {
        "print_format": "paperback",
        "trim_size": "6x9",
        "paper_type": "cream_bw",
        "page_count": 200,
        "inside_margin_in": 0.5,
    }
    res = client.post("/api/v1/ai/validate/print-specs", json=valid_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_valid"] is True

    # Invalid spec (cream paper > 776 pages)
    invalid_payload = {
        "print_format": "paperback",
        "trim_size": "6x9",
        "paper_type": "cream_bw",
        "page_count": 780,
    }
    res_inv = client.post("/api/v1/ai/validate/print-specs", json=invalid_payload, headers=headers)
    assert res_inv.status_code == 200
    assert res_inv.json()["is_valid"] is False
    assert any(e["rule_id"] == "KDP-PRN-001" for e in res_inv.json()["blocking_errors"])


def test_validate_metadata_endpoint(client: TestClient, test_user: User):
    """POST /api/v1/ai/validate/metadata checks title length, keywords, and HTML description."""
    headers = get_auth_headers(client, test_user)

    # Valid metadata
    valid_payload = {
        "title": "Good Book Title",
        "keywords": ["finance", "money"],
        "description_html": "<p>A <b>great</b> book.</p>",
    }
    res = client.post("/api/v1/ai/validate/metadata", json=valid_payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_valid"] is True

    # Invalid metadata (script tag in description)
    invalid_payload = {
        "title": "Good Book Title",
        "keywords": ["finance"],
        "description_html": "<p>A book with <script>alert(1)</script></p>",
    }
    res_inv = client.post("/api/v1/ai/validate/metadata", json=invalid_payload, headers=headers)
    assert res_inv.status_code == 200
    assert res_inv.json()["is_valid"] is False
    assert any("Prohibited HTML tag" in e["message"] for e in res_inv.json()["blocking_errors"])
