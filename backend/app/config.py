"""Centralized application settings for all runtime environments."""

import json
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _to_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _to_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./patrol_pro.db")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "please-change-this-secret-key-for-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    SESSION_IDLE_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "30"))

    # Rate limiting
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = _to_bool(os.getenv("DEBUG"), True)
    RELOAD: bool = _to_bool(os.getenv("RELOAD"), True)

    # CORS
    ALLOWED_ORIGINS: list[str] = _to_list(
        os.getenv("ALLOWED_ORIGINS"),
        [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
        ],
    )

    # Security headers
    ENABLE_SECURITY_HEADERS: bool = _to_bool(os.getenv("ENABLE_SECURITY_HEADERS"), True)
    ENABLE_RATE_LIMITING: bool = _to_bool(os.getenv("ENABLE_RATE_LIMITING"), True)

    # API
    API_TITLE: str = os.getenv("API_TITLE", "Patrol Pro API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv("API_DESCRIPTION", "Professional security patrol management platform")

    def validate_production_safety(self) -> None:
        if not self.DEBUG and self.SECRET_KEY == "please-change-this-secret-key-for-production":
            raise RuntimeError("SECRET_KEY must be set to a strong unique value when DEBUG=false")
        if not self.DEBUG and any(origin == "*" for origin in self.ALLOWED_ORIGINS):
            raise RuntimeError("ALLOWED_ORIGINS cannot contain '*' when DEBUG=false")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
