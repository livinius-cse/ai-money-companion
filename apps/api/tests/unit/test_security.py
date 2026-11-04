import base64
import time
from datetime import timedelta
import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_csrf_token,
    validate_csrf_token,
    validate_request_origin,
    _strict_urlsafe_b64decode,
    _strict_urlsafe_b64encode,
)


# ==========================================
# 1. Password Hashing & Verification Tests
# ==========================================

def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = get_password_hash(password)

    assert hashed != password
    assert hashed.startswith("$argon2")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password(password, "invalid_hash_string") is False


# ==========================================
# 2. JWT Access Token Security Tests
# ==========================================

def test_jwt_access_token_creation_and_decoding():
    subject = "user-12345"
    token = create_access_token(subject=subject, claims={"role": "admin"})

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == subject
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_protected_claims_override_rejection():
    # Attempting to override 'sub', 'iat', or 'exp' via custom claims must raise ValueError
    with pytest.raises(ValueError, match="Custom claims cannot overwrite protected claims"):
        create_access_token("valid_user", claims={"sub": "imposter_user"})

    with pytest.raises(ValueError, match="Custom claims cannot overwrite protected claims"):
        create_access_token("valid_user", claims={"exp": 9999999999})

    with pytest.raises(ValueError, match="Custom claims cannot overwrite protected claims"):
        create_access_token("valid_user", claims={"iat": 1000000000})


def test_jwt_expired_token():
    subject = "user-expired"
    token = create_access_token(subject=subject, expires_delta=timedelta(minutes=-10))
    assert decode_access_token(token) is None


def test_jwt_algorithm_restriction():
    # Attempting to forge a token with 'none' algorithm
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "attacker", "exp": int(time.time()) + 3600, "iat": int(time.time())}
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(b'{"sub":"attacker","exp":9999999999,"iat":1000000000}').decode().rstrip("=")
    unsigned_token = f"{header_b64}.{payload_b64}."

    assert decode_access_token(unsigned_token) is None


def test_jwt_missing_required_claims():
    # Token missing 'sub'
    token_no_sub = jwt.encode(
        {"exp": int(time.time()) + 3600, "iat": int(time.time())},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert decode_access_token(token_no_sub) is None

    # Token with empty string 'sub'
    token_empty_sub = jwt.encode(
        {"sub": "", "exp": int(time.time()) + 3600, "iat": int(time.time())},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert decode_access_token(token_empty_sub) is None

    # Token missing 'exp'
    token_no_exp = jwt.encode(
        {"sub": "user-1", "iat": int(time.time())},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert decode_access_token(token_no_exp) is None


# ==========================================
# 3. Base64URL Strict Decoding Tests
# ==========================================

def test_strict_b64url_decoding():
    data = b"Hello, World! 12345"
    encoded = _strict_urlsafe_b64encode(data)

    # Valid decode
    decoded = _strict_urlsafe_b64decode(encoded)
    assert decoded == data

    # Rejection of invalid characters
    with pytest.raises(ValueError, match="Invalid Base64URL character"):
        _strict_urlsafe_b64decode("abc@123")

    with pytest.raises(ValueError, match="Invalid Base64URL character"):
        _strict_urlsafe_b64decode("abc+123")  # Standard base64 '+' not allowed in urlsafe

    with pytest.raises(ValueError, match="Invalid Base64URL character"):
        _strict_urlsafe_b64decode("abc/123")  # Standard base64 '/' not allowed in urlsafe

    # Rejection of invalid length (len % 4 == 1 cannot exist in base64)
    with pytest.raises(ValueError, match="Invalid Base64URL length"):
        _strict_urlsafe_b64decode("a")

    # Rejection of non-string / empty
    with pytest.raises(ValueError):
        _strict_urlsafe_b64decode("")


# ==========================================
# 4. CSRF Identity Binding & Validation Tests
# ==========================================

def test_csrf_token_generation_and_valid_validation():
    token = generate_csrf_token(identity="anonymous")
    assert token is not None
    assert "." in token
    assert validate_csrf_token(token, expected_identity="anonymous") is True


def test_csrf_identity_binding_enforcement():
    user_a_token = generate_csrf_token(identity="user-a")
    user_b_token = generate_csrf_token(identity="user-b")
    anon_token = generate_csrf_token(identity="anonymous")

    # Exact matches pass
    assert validate_csrf_token(user_a_token, expected_identity="user-a") is True
    assert validate_csrf_token(user_b_token, expected_identity="user-b") is True
    assert validate_csrf_token(anon_token, expected_identity="anonymous") is True

    # Identity mismatches fail
    assert validate_csrf_token(user_a_token, expected_identity="user-b") is False
    assert validate_csrf_token(user_b_token, expected_identity="user-a") is False
    assert validate_csrf_token(anon_token, expected_identity="user-a") is False
    assert validate_csrf_token(user_a_token, expected_identity="anonymous") is False


def test_csrf_missing_identity_rejection():
    token = generate_csrf_token(identity="user-a")

    # None or empty expected_identity must NEVER silently pass
    assert validate_csrf_token(token, expected_identity=None) is False  # type: ignore
    assert validate_csrf_token(token, expected_identity="") is False


def test_csrf_tampered_signature_rejection():
    token = generate_csrf_token(identity="anonymous")
    payload_b64, sig_b64 = token.split(".")

    # Tampered signature bytes
    tampered_sig = sig_b64[:-2] + "AA"
    assert validate_csrf_token(f"{payload_b64}.{tampered_sig}", expected_identity="anonymous") is False

    # Truncated signature (wrong byte length)
    truncated_sig = sig_b64[:10]
    assert validate_csrf_token(f"{payload_b64}.{truncated_sig}", expected_identity="anonymous") is False


def test_csrf_malformed_token_structure():
    # No dot
    assert validate_csrf_token("nodottoken", expected_identity="anonymous") is False
    # Multiple dots
    assert validate_csrf_token("a.b.c", expected_identity="anonymous") is False
    # Non-base64 characters in payload or sig
    assert validate_csrf_token("bad!payload.bad!sig", expected_identity="anonymous") is False
    # Empty string
    assert validate_csrf_token("", expected_identity="anonymous") is False


def test_csrf_expired_token():
    token = generate_csrf_token(identity="user-a")
    # Expired token (simulated by negative max_age)
    assert validate_csrf_token(token, expected_identity="user-a", max_age_seconds=-1) is False


def test_csrf_future_timestamp_token():
    # Construct token with timestamp 5 minutes into the future
    future_time = str(int(time.time()) + 300)
    fake_payload = f"{future_time}:user-a:salt123456".encode()
    fake_sig = _strict_urlsafe_b64encode(b"0" * 32)
    fake_token = f"{_strict_urlsafe_b64encode(fake_payload)}.{fake_sig}"

    assert validate_csrf_token(fake_token, expected_identity="user-a") is False


# ==========================================
# 5. Origin & Referer Validation Security Tests
# ==========================================

def test_request_origin_valid_allowed():
    allowed = ["http://localhost:3000", "http://127.0.0.1:3000", "https://author.kdp-os.com"]

    # Valid exact origins pass
    assert validate_request_origin("http://localhost:3000", None, allowed) is True
    assert validate_request_origin("http://127.0.0.1:3000", None, allowed) is True
    assert validate_request_origin("https://author.kdp-os.com", None, allowed) is True

    # Case insensitivity (HTTP vs http)
    assert validate_request_origin("HTTP://LOCALHOST:3000", None, allowed) is True

    # Origin headers containing any path, including '/', must be strictly REJECTED
    assert validate_request_origin("http://localhost:3000/", None, allowed) is False
    assert validate_request_origin("http://localhost:3000/path", None, allowed) is False

    # In contrast, Referer headers with paths or trailing slashes are valid and accepted
    assert validate_request_origin(None, "http://localhost:3000/", allowed) is True
    assert validate_request_origin(None, "http://localhost:3000/dashboard", allowed) is True


def test_request_referer_fallback():
    allowed = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Valid referer with deep path and query passes when Origin is absent
    assert validate_request_origin(None, "http://localhost:3000/dashboard/books?tab=drafts", allowed) is True
    assert validate_request_origin(None, "http://127.0.0.1:3000/login", allowed) is True

    # Cross-site referer fails
    assert validate_request_origin(None, "https://evil.com/attack", allowed) is False


def test_request_missing_origin_and_referer():
    allowed = ["http://localhost:3000"]

    # Default policy: Browser requests without Origin AND Referer must be REJECTED
    assert validate_request_origin(None, None, allowed, allow_missing=False) is False
    assert validate_request_origin("", "", allowed, allow_missing=False) is False

    # Explicit non-browser policy: permitted only when allow_missing=True
    assert validate_request_origin(None, None, allowed, allow_missing=True) is True


def test_request_origin_malformed_rejections():
    allowed = ["http://localhost:3000"]

    # Paths in Origin header (RFC 6454 violation), including root '/', must be rejected
    assert validate_request_origin("http://localhost:3000/", None, allowed) is False
    assert validate_request_origin("http://localhost:3000/path", None, allowed) is False
    assert validate_request_origin("http://localhost:3000/dashboard?a=1", None, allowed) is False

    # Credentials in Origin (user:pass@host) must be rejected
    assert validate_request_origin("http://admin:secret@localhost:3000", None, allowed) is False
    assert validate_request_origin(None, "http://admin:secret@localhost:3000/dashboard", allowed) is False

    # 'null' Origin (sandboxed iframe / privacy context) must be rejected
    assert validate_request_origin("null", None, allowed) is False
    assert validate_request_origin("NULL", None, allowed) is False

    # Disallowed URL schemes
    assert validate_request_origin("ftp://localhost:3000", None, allowed) is False
    assert validate_request_origin("javascript:alert(1)", None, allowed) is False
    assert validate_request_origin("data:text/html,test", None, allowed) is False
    assert validate_request_origin("file:///etc/passwd", None, allowed) is False

    # Malformed non-URL strings
    assert validate_request_origin("not a url at all", None, allowed) is False
    assert validate_request_origin("://missing-scheme", None, allowed) is False
