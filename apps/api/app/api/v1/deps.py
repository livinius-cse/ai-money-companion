from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import (
    decode_access_token,
    validate_csrf_token,
    validate_request_origin,
)
from app.db.session import get_db
from app.models.user import User


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract access token from HttpOnly cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Dependency to retrieve authenticated user from JWT token in cookie or header."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency returning User if authenticated, None otherwise."""
    token = get_token_from_request(request)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    user = db.scalar(select(User).where(User.id == payload["sub"]))
    if not user or not user.is_active:
        return None

    return user


def verify_csrf(
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> None:
    """
    Validates CSRF for state-changing HTTP requests.
    Enforces:
    1. Origin / Referer validation against ALLOWED_ORIGINS.
    2. Signed CSRF token validation via X-CSRF-Token header.
    3. Session/User identity binding if authenticated.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")

    # 1. Validate Origin / Referer
    if not validate_request_origin(origin, referer, settings.ALLOWED_ORIGINS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-origin request rejected.",
        )

    # 2. Extract CSRF token from header
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing in X-CSRF-Token header.",
        )

    # 3. Verify signed token with strictly expected identity binding
    expected_identity = current_user.id if current_user else "anonymous"
    is_valid = validate_csrf_token(csrf_token, expected_identity=expected_identity)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid, expired, or bound to a different session.",
        )
