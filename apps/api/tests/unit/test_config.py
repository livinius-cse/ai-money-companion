import pytest
from pydantic import ValidationError
from app.core.config import Settings


VALID_SECRET_1 = "valid_secret_key_1_at_least_32_characters_long_12345"
VALID_SECRET_2 = "valid_secret_key_2_at_least_32_characters_long_67890"


def test_valid_settings_configuration():
    cfg = Settings(
        SECRET_KEY=VALID_SECRET_1,
        CSRF_SECRET_KEY=VALID_SECRET_2,
        ALGORITHM="HS256",
        SECURE_COOKIE=False,
        COOKIE_SAMESITE="strict",
        RATE_LIMIT_LOGIN_PER_MINUTE=5,
    )
    assert cfg.SECRET_KEY == VALID_SECRET_1
    assert cfg.CSRF_SECRET_KEY == VALID_SECRET_2
    assert cfg.ALGORITHM == "HS256"
    assert cfg.COOKIE_SAMESITE == "strict"
    assert cfg.SECURE_COOKIE is False
    assert cfg.RATE_LIMIT_LOGIN_PER_MINUTE == 5


def test_missing_secret_keys():
    with pytest.raises(ValidationError):
        # Empty kwargs without env fallback for secrets
        Settings(
            _env_file=None,  # Do not read from .env
            SECRET_KEY="",
            CSRF_SECRET_KEY=VALID_SECRET_2,
        )

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY="",
        )


def test_weak_secret_key_rejection():
    # Secret less than 32 characters
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SECRET_KEY="too_short_key_under_32_chars",
            CSRF_SECRET_KEY=VALID_SECRET_2,
        )
    assert "at least 32 characters" in str(exc_info.value)


def test_placeholder_secret_rejection():
    # Known placeholder values must be rejected
    placeholders = [
        "dev-secret-key-change-in-production-ai-money-companion-2026",
        "change-me-please-generate-a-new-secret-key-32chars",
        "your-secret-key-at-least-32-chars-long-placeholder",
        "replace_with_a_secure_random_key_min_32_chars",
        "GENERATE_AND_PASTE_A_32_CHAR_SECRET_KEY_HERE",
    ]
    for placeholder in placeholders:
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY=placeholder,
                CSRF_SECRET_KEY=VALID_SECRET_2,
            )
        assert "placeholder" in str(exc_info.value).lower() or "insecure" in str(exc_info.value).lower()


def test_identical_secrets_rejection():
    # SECRET_KEY and CSRF_SECRET_KEY must not be the same string
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_1,
        )
    assert "must be distinct" in str(exc_info.value)


def test_invalid_jwt_algorithm():
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            ALGORITHM="none",  # type: ignore
        )

    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            ALGORITHM="RS256",  # type: ignore
        )


def test_invalid_samesite_configuration():
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            COOKIE_SAMESITE="invalid_samesite",  # type: ignore
        )


def test_samesite_none_requires_secure_cookie():
    # SameSite=none with SECURE_COOKIE=False must be rejected
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            COOKIE_SAMESITE="none",
            SECURE_COOKIE=False,
        )
    assert "SECURE_COOKIE must be True when COOKIE_SAMESITE is 'none'" in str(exc_info.value)

    # SameSite=none with SECURE_COOKIE=True must be accepted
    cfg = Settings(
        SECRET_KEY=VALID_SECRET_1,
        CSRF_SECRET_KEY=VALID_SECRET_2,
        COOKIE_SAMESITE="none",
        SECURE_COOKIE=True,
    )
    assert cfg.COOKIE_SAMESITE == "none"
    assert cfg.SECURE_COOKIE is True


def test_rate_limit_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            RATE_LIMIT_LOGIN_PER_MINUTE=0,
        )

    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY=VALID_SECRET_1,
            CSRF_SECRET_KEY=VALID_SECRET_2,
            RATE_LIMIT_LOGIN_PER_MINUTE=-5,
        )
