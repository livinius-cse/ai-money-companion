import base64
import binascii
import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# Initialize Argon2 Password Hasher
_pwd_hasher = PasswordHasher()


def get_password_hash(password: str) -> str:
    """Generate secure Argon2id password hash."""
    return _pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored Argon2id hash."""
    try:
        return _pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


PROTECTED_JWT_CLAIMS = {"sub", "iat", "exp"}


def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create signed JWT access token with restricted algorithm and required claims."""
    if claims:
        conflicting = PROTECTED_JWT_CLAIMS.intersection(claims.keys())
        if conflicting:
            raise ValueError(
                f"Custom claims cannot overwrite protected claims: {sorted(conflicting)}"
            )

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and strictly validate a JWT access token.
    Enforces algorithm whitelist and verifies required claims (sub, exp, iat).
    """
    if not token or not isinstance(token, str):
        return None

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={
                "require": ["sub", "exp", "iat"],
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        # Ensure subject is a non-empty string
        sub = payload.get("sub")
        if not sub or not isinstance(sub, str):
            return None
        return payload
    except (jwt.PyJWTError, ValueError):
        return None


# ==========================================
# Strict Base64URL Encoding / Decoding
# ==========================================

_BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _strict_urlsafe_b64encode(data: bytes) -> str:
    """Encode bytes to an unpadded Base64URL string."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _strict_urlsafe_b64decode(s: str) -> bytes:
    """
    Strictly decode an unpadded or padded Base64URL string.
    Rejects non-string inputs, invalid characters, malformed lengths, or invalid padding.
    """
    if not s or not isinstance(s, str):
        raise ValueError("Input must be a non-empty string.")

    stripped = s.rstrip("=")
    if not stripped or not _BASE64URL_PATTERN.match(stripped):
        raise ValueError("Invalid Base64URL character detected.")

    # In base64, a valid block cannot have length % 4 == 1
    rem = len(stripped) % 4
    if rem == 1:
        raise ValueError("Invalid Base64URL length.")

    padding = "=" * (4 - rem) if rem != 0 else ""
    return base64.urlsafe_b64decode((stripped + padding).encode("ascii"))


# ==========================================
# Signed & Session-Bound CSRF Token Engine
# ==========================================

def generate_csrf_token(identity: str = "anonymous") -> str:
    """
    Generate an HMAC-SHA256 signed CSRF token bound to an explicit identity.
    Format: <base64url(payload)>.<base64url(hmac_signature)>
    Payload: <timestamp>:<identity>:<salt>
    """
    if not identity or not isinstance(identity, str) or ":" in identity:
        raise ValueError("CSRF identity must be a non-empty string without colon characters.")

    timestamp = str(int(time.time()))
    salt = secrets.token_hex(8)
    payload_str = f"{timestamp}:{identity}:{salt}"
    payload_bytes = payload_str.encode("utf-8")

    signature = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()

    return f"{_strict_urlsafe_b64encode(payload_bytes)}.{_strict_urlsafe_b64encode(signature)}"


def validate_csrf_token(
    token: str,
    expected_identity: str,
    max_age_seconds: int = 86400,  # 24 hours
) -> bool:
    """
    Validate HMAC signature, timestamp age, payload structure, and exact bound identity.
    Identity validation is mandatory: expected_identity must be a non-empty string
    (e.g., user_id for authenticated sessions, 'anonymous' for unauthenticated requests).
    Never silently skips identity validation.
    """
    if not expected_identity or not isinstance(expected_identity, str):
        return False

    if not token or not isinstance(token, str):
        return False

    parts = token.split(".")
    if len(parts) != 2:
        return False

    payload_b64, signature_b64 = parts

    try:
        payload_bytes = _strict_urlsafe_b64decode(payload_b64)
        signature = _strict_urlsafe_b64decode(signature_b64)
    except (ValueError, binascii.Error):
        return False

    # Signature must be exactly 32 bytes (SHA-256 digest length)
    if len(signature) != 32:
        return False

    # Verify HMAC signature with constant-time comparison
    expected_sig = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(signature, expected_sig):
        return False

    # Parse and validate payload
    try:
        payload_str = payload_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return False

    fields = payload_str.split(":")
    if len(fields) != 3:
        return False

    timestamp_str, token_identity, salt = fields
    if not timestamp_str or not token_identity or not salt:
        return False

    try:
        token_time = int(timestamp_str)
    except ValueError:
        return False

    now = int(time.time())

    # Check expiration and prevent future timestamps (allowing 60s clock skew)
    if token_time < 0 or (now - token_time) > max_age_seconds:
        return False
    if token_time > (now + 60):
        return False

    # Mandatory constant-time identity validation
    if not hmac.compare_digest(token_identity, expected_identity):
        return False

    return True


# ==========================================
# Strict Origin & Referer Validation
# ==========================================

def _normalize_origin(url_str: str, is_origin_header: bool = True) -> str:
  """
  Parse and strictly validate an Origin or Referer URL.
  Returns normalized '<scheme>://<netloc>' in lowercase.
  Raises ValueError if the URL is malformed, uses unexpected schemes,
  contains credentials, or has paths in an Origin header.
  """
  if not url_str or not isinstance(url_str, str):
    raise ValueError("URL string must be non-empty.")

  clean_url = url_str.strip()
  if clean_url.lower() == "null":
    raise ValueError("Origin 'null' is not permitted.")

  parsed = urlparse(clean_url)

  # Enforce HTTP/HTTPS scheme
  if parsed.scheme.lower() not in ("http", "https"):
    raise ValueError(f"Disallowed URL scheme: {parsed.scheme}")

  # Disallow credentials in origin/referer (userinfo like http://user:pass@host)
  if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
    raise ValueError("User credentials are not permitted in Origin or Referer.")

  if not parsed.netloc:
    raise ValueError("Missing hostname in URL.")

  # Origin headers (RFC 6454) must not contain any path (including '/'), query, or fragment
  if is_origin_header:
    if parsed.path or parsed.query or parsed.fragment or parsed.params:
      raise ValueError("Origin header must not contain any path (including '/'), queries, or fragments.")

  return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def validate_request_origin(
    origin: Optional[str],
    referer: Optional[str],
    allowed_origins: List[str],
    allow_missing: bool = False,
) -> bool:
    """
    Validate that request Origin or Referer matches the configured ALLOWED_ORIGINS list.
    Rejects:
    - Missing Origin AND Referer by default (browser state-changing policy).
    - Malformed URLs, unexpected schemes, credentials in URLs.
    - Paths/queries in Origin headers.
    - 'null' origin.
    - Cross-site / unlisted origins.

    Non-browser clients must adhere to an explicit policy: either provide a valid
    Origin/Referer header or set allow_missing=True where explicitly permitted.
    """
    if not allowed_origins:
        return False

    normalized_allowed = set()
    for o in allowed_origins:
        try:
            normalized_allowed.add(_normalize_origin(o, is_origin_header=False))
        except ValueError:
            continue

    if not normalized_allowed:
        return False

    candidate_origin = None

    # 1. Prefer Origin header if present
    if origin:
        try:
            candidate_origin = _normalize_origin(origin, is_origin_header=True)
        except ValueError:
            return False

    # 2. Fall back to Referer header if Origin is absent
    elif referer:
        try:
            candidate_origin = _normalize_origin(referer, is_origin_header=False)
        except ValueError:
            return False

    # 3. Handle missing headers
    else:
        return allow_missing

    return candidate_origin in normalized_allowed
