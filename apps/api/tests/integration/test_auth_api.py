import concurrent.futures
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_csrf_token
from app.main import app
from app.models.user import User
from app.models.system_state import SystemState


def test_health_check(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == "AI Money Companion"


def test_get_csrf_token(client: TestClient):
    response = client.get("/api/v1/auth/csrf")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert "." in data["csrf_token"]
    assert "csrf_token" in response.cookies


def test_initial_admin_setup_lifecycle(client: TestClient, anon_csrf_token: str):
    # Setup first admin
    headers = {
        "X-CSRF-Token": anon_csrf_token,
        "Origin": "http://localhost:3000",
    }
    payload = {
        "email": "firstadmin@example.com",
        "password": "SecurePassword123!",
        "full_name": "First Admin",
    }
    response = client.post("/api/v1/auth/setup", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "firstadmin@example.com"
    assert data["is_admin"] is True
    assert "access_token" in response.cookies
    assert "csrf_token" in response.cookies

    # After first setup, the client is now authenticated with user-bound session and CSRF cookie
    new_csrf_token = response.cookies["csrf_token"]
    auth_headers = {
        "X-CSRF-Token": new_csrf_token,
        "Origin": "http://localhost:3000",
    }

    # Duplicate setup attempt must fail with 400
    dup_response = client.post("/api/v1/auth/setup", json=payload, headers=auth_headers)
    assert dup_response.status_code == 400
    assert "already complete" in dup_response.json()["detail"]


def test_concurrent_initial_admin_setup(anon_csrf_token: str, db_session: Session):
    """
    Test that concurrent requests to /auth/setup are serialized at the database level,
    resulting in exactly one administrator user created and the others rejected.
    """
    headers = {
        "X-CSRF-Token": anon_csrf_token,
        "Origin": "http://localhost:3000",
    }

    def attempt_setup(idx: int):
        c = TestClient(app, base_url="http://localhost:3000")
        payload = {
            "email": f"admin_concurrent_{idx}@example.com",
            "password": "SecurePassword123!",
            "full_name": f"Admin {idx}",
        }
        return c.post("/api/v1/auth/setup", json=payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(attempt_setup, range(5)))

    status_codes = [r.status_code for r in responses]
    assert status_codes.count(201) == 1
    assert status_codes.count(400) == 4

    user_count = db_session.scalar(select(func.count(User.id)))
    assert user_count == 1

    lock_count = db_session.scalar(select(func.count(SystemState.key)))
    assert lock_count == 1


def test_login_success(client: TestClient, test_user, anon_csrf_token: str):
    headers = {
        "X-CSRF-Token": anon_csrf_token,
        "Origin": "http://localhost:3000",
    }
    payload = {
        "email": test_user.email,
        "password": "StrongPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert "access_token" in response.cookies
    assert "csrf_token" in response.cookies


def test_login_invalid_password(client: TestClient, test_user, anon_csrf_token: str):
    headers = {
        "X-CSRF-Token": anon_csrf_token,
        "Origin": "http://localhost:3000",
    }
    payload = {
        "email": test_user.email,
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=payload, headers=headers)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_rate_limiting(client: TestClient, test_user, anon_csrf_token: str):
    headers = {
        "X-CSRF-Token": anon_csrf_token,
        "Origin": "http://localhost:3000",
    }
    payload = {
        "email": test_user.email,
        "password": "BadPassword!",
    }

    # 5 attempts should return 401
    for _ in range(5):
        resp = client.post("/api/v1/auth/login", json=payload, headers=headers)
        assert resp.status_code == 401

    # 6th attempt within the 1-minute window must be blocked with 429
    blocked_resp = client.post("/api/v1/auth/login", json=payload, headers=headers)
    assert blocked_resp.status_code == 429
    assert "Too many login attempts" in blocked_resp.json()["detail"]
    assert "Retry-After" in blocked_resp.headers


def test_csrf_rejection_missing_header(client: TestClient, test_user):
    # Missing X-CSRF-Token header
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 403
    assert "CSRF token missing" in response.json()["detail"]


def test_csrf_rejection_cross_site_origin(client: TestClient, test_user, anon_csrf_token: str):
    # Cross-site origin from attacker domain
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "https://attacker-domain.com",
        },
    )
    assert response.status_code == 403
    assert "Cross-origin request rejected" in response.json()["detail"]


def test_protected_me_endpoint(client: TestClient, test_user, anon_csrf_token: str):
    # Unauthenticated call returns 401
    unauth_resp = client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # Log in to get session cookie
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://localhost:3000",
        },
    )
    assert login_resp.status_code == 200

    # Call /api/v1/auth/me with cookies automatically stored in client session
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id


def test_logout(client: TestClient, test_user, anon_csrf_token: str):
    # Login first
    client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://localhost:3000",
        },
    )

    # Issue user-bound CSRF token
    user_csrf = generate_csrf_token(identity=test_user.id)

    # Logout
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={
            "X-CSRF-Token": user_csrf,
            "Origin": "http://localhost:3000",
        },
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # Check Set-Cookie headers for deletion attributes
    set_cookie_headers = [
        v for k, v in logout_resp.headers.raw if k.decode().lower() == "set-cookie"
    ]
    set_cookie_str = " ".join([h.decode() for h in set_cookie_headers])

    # Both access_token and csrf_token must be instructed to expire/delete
    assert "access_token" in set_cookie_str
    assert "csrf_token" in set_cookie_str

    # Verify matching path attributes
    assert "path=/api" in set_cookie_str.lower()
    assert "path=/" in set_cookie_str.lower()

    # Verify max-age=0 or expired date
    assert "max-age=0" in set_cookie_str.lower()

    # Verify matching SameSite attribute
    assert f"samesite={settings.COOKIE_SAMESITE.lower()}" in set_cookie_str.lower()

    # Verify HttpOnly preserved on access_token deletion
    access_token_header = next(
        h.decode() for h in set_cookie_headers if "access_token" in h.decode()
    )
    assert "httponly" in access_token_header.lower()

    # After logout, accessing /me should fail with 401
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401


def test_csrf_rejection_missing_origin_and_referer(client: TestClient, test_user, anon_csrf_token: str):
    # Missing both Origin and Referer on state-changing request
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={"X-CSRF-Token": anon_csrf_token},
    )
    assert response.status_code == 403
    assert "Cross-origin request rejected" in response.json()["detail"]


def test_csrf_rejection_malformed_origin(client: TestClient, test_user, anon_csrf_token: str):
    # Origin with path (RFC 6454 violation)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://localhost:3000/login",
        },
    )
    assert response.status_code == 403

    # Origin with credentials
    cred_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://user:pass@localhost:3000",
        },
    )
    assert cred_resp.status_code == 403

    # 'null' Origin
    null_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "null",
        },
    )
    assert null_resp.status_code == 403


def test_authenticated_user_csrf_identity_mismatch(client: TestClient, test_user, anon_csrf_token: str):
    # 1. Log in to establish authenticated session
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "StrongPassword123!"},
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://localhost:3000",
        },
    )
    assert login_resp.status_code == 200

    # 2. Attempt logout using an anonymous CSRF token instead of the user's bound token
    logout_resp = client.post(
        "/api/v1/auth/logout",
        headers={
            "X-CSRF-Token": anon_csrf_token,
            "Origin": "http://localhost:3000",
        },
    )
    # Must be strictly rejected with 403 because token identity != test_user.id
    assert logout_resp.status_code == 403
    assert "CSRF token invalid" in logout_resp.json()["detail"]
