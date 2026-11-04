from typing import List, Literal, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_INSECURE_SECRETS = {
    "change_this_to_a_secure_random_key",
    "change-me",
    "changeme",
    "secret",
    "secretkey",
    "dev-secret-key-change-in-production-ai-money-companion-2026",
    "dev-csrf-secret-key-change-in-production-ai-money-2026",
    "your-secret-key-here",
    "your-secret-key-at-least-32-chars",
    "your-csrf-secret-key-at-least-32-chars",
    "replace_with_a_secure_random_key_min_32_chars",
    "replace-with-a-secure-random-key",
    "0123456789abcdef0123456789abcdef",
    "placeholder",
    "generate_and_paste_a_32_char_secret_key_here",
    "generate_and_paste_a_32_char_csrf_key_here",
}

PLACEHOLDER_SUBSTRINGS = (
    "change-in-production",
    "change_this",
    "change-this",
    "change-me",
    "changeme",
    "your-secret",
    "replace_with",
    "replace-with",
    "generate_and_paste",
    "placeholder",
)


def _validate_secret(value: str, field_name: str) -> str:
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string.")
    cleaned = value.strip()
    if len(cleaned) < 32:
        raise ValueError(
            f"{field_name} must be at least 32 characters long for cryptographic security (got {len(cleaned)})."
        )
    lowered = cleaned.lower()
    if lowered in KNOWN_INSECURE_SECRETS:
        raise ValueError(f"{field_name} cannot use known placeholder or insecure value.")
    for sub in PLACEHOLDER_SUBSTRINGS:
        if sub in lowered:
            raise ValueError(
                f"{field_name} contains placeholder indicator '{sub}'. Please configure a random key."
            )
    return cleaned


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Money Companion API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security & Auth (Required: must be provided via environment or .env, min 32 chars)
    SECRET_KEY: str
    CSRF_SECRET_KEY: str
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, gt=0)
    SECURE_COOKIE: bool = False  # False for local HTTP development, True for production HTTPS
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"

    # Rate Limiting (must be positive)
    RATE_LIMIT_LOGIN_PER_MINUTE: int = Field(default=5, gt=0)

    # CORS & Allowed Origins for CSRF verification
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database & Storage
    DATABASE_URL: str = "sqlite:///./ai_money_companion.db"
    STORAGE_DIR: str = "./storage"

    # AI Configuration (Mock by default for zero-cost offline development)
    AI_PROVIDER: str = "mock"
    GEMINI_API_KEY: Optional[str] = None

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        return _validate_secret(v, "SECRET_KEY")

    @field_validator("CSRF_SECRET_KEY", mode="before")
    @classmethod
    def validate_csrf_secret_key(cls, v: str) -> str:
        return _validate_secret(v, "CSRF_SECRET_KEY")

    @model_validator(mode="after")
    def validate_security_constraints(self) -> "Settings":
        # SECRET_KEY and CSRF_SECRET_KEY must be distinct
        if self.SECRET_KEY == self.CSRF_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY and CSRF_SECRET_KEY must be distinct cryptographic keys."
            )

        # SameSite=none requires SECURE_COOKIE=True
        if self.COOKIE_SAMESITE == "none" and not self.SECURE_COOKIE:
            raise ValueError(
                "SECURE_COOKIE must be True when COOKIE_SAMESITE is 'none' (browsers reject SameSite=None without Secure flag)."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
