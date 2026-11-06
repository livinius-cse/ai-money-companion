import threading
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, OperationalError, DBAPIError

from app.core.config import settings
from app.core.rate_limiter import enforce_login_rate_limit
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.models.system_state import SystemState
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    UserResponse,
    CSRFResponse,
    AuthStatusResponse,
    MessageResponse,
)
from app.api.v1.deps import (
    get_current_user,
    get_optional_current_user,
    verify_csrf,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf", response_model=CSRFResponse)
def get_csrf_token(
    response: Response,
    current_user: User = Depends(get_optional_current_user),
):
    """
    Issue a signed CSRF token bound to the current session (or anonymous).
    Sets the readable csrf_token cookie for the client.
    """
    identity = current_user.id if current_user else "anonymous"
    token = generate_csrf_token(identity=identity)

    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # Client JavaScript must read this to set X-CSRF-Token header
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.SECURE_COOKIE,
        path="/",
        max_age=86400,
    )
    return CSRFResponse(csrf_token=token)


INITIAL_ADMIN_SETUP_LOCK_KEY = "INITIAL_ADMIN_SETUP_LOCK"


_setup_lock = threading.Lock()


@router.post(
    "/setup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def setup_initial_admin(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Bootstrap the initial root administrator account on first run.
    Uses process-level mutex and database-level serialization (BEGIN IMMEDIATE on SQLite)
    with an atomic uniqueness lock record (SystemState) to prevent race conditions.
    """
    with _setup_lock:
        # 1. Enforce SQLite write lock serialization if running on SQLite
        bind = db.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            try:
                db.execute(text("BEGIN IMMEDIATE"))
            except Exception:
                pass

        # 2. Check if setup lock record already exists
        existing_lock = db.scalar(
            select(SystemState).where(SystemState.key == INITIAL_ADMIN_SETUP_LOCK_KEY)
        )
        if existing_lock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial setup is already complete. Please log in.",
            )

        # 3. Check existing user count
        user_count = db.scalar(select(func.count(User.id)))
        if user_count and user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial setup is already complete. Please log in.",
            )

        # 4. Atomically insert setup lock and admin user
        lock_record = SystemState(
            key=INITIAL_ADMIN_SETUP_LOCK_KEY,
            value="COMPLETED",
        )
        hashed_pw = get_password_hash(payload.password)
        admin_user = User(
            email=payload.email,
            hashed_password=hashed_pw,
            full_name=payload.full_name or "Publisher Admin",
            is_active=True,
            is_admin=True,
        )
        db.add(lock_record)
        db.add(admin_user)

        try:
            db.commit()
            db.refresh(admin_user)
        except (IntegrityError, OperationalError, DBAPIError, Exception):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Initial setup is already complete. Please log in.",
            )

        # Issue auth cookies immediately
        token = create_access_token(subject=admin_user.id)
        csrf_token = generate_csrf_token(identity=admin_user.id)

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.SECURE_COOKIE,
            path="/api",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            samesite=settings.COOKIE_SAMESITE,
            secure=settings.SECURE_COOKIE,
            path="/",
            max_age=86400,
        )

        return admin_user


@router.post(
    "/login",
    response_model=UserResponse,
    dependencies=[Depends(enforce_login_rate_limit), Depends(verify_csrf)],
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate user credentials, enforce rate-limiting, and issue secure cookies.
    """
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    # Issue JWT access token
    token = create_access_token(subject=user.id)
    # Issue signed CSRF token bound to this user ID
    csrf_token = generate_csrf_token(identity=user.id)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.SECURE_COOKIE,
        path="/api",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.SECURE_COOKIE,
        path="/",
        max_age=86400,
    )

    return user


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(verify_csrf)],
)
def logout(response: Response):
    """Clear session and CSRF cookies using matching paths and security attributes."""
    response.delete_cookie(
        key="access_token",
        path="/api",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.SECURE_COOKIE,
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.SECURE_COOKIE,
    )
    return MessageResponse(message="Successfully logged out.")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve profile of currently authenticated user."""
    return current_user


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status(current_user: User = Depends(get_optional_current_user)):
    """Check authentication status without throwing 401."""
    if current_user:
        return AuthStatusResponse(authenticated=True, user=UserResponse.model_validate(current_user))
    return AuthStatusResponse(authenticated=False, user=None)
