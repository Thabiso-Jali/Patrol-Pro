"""Typed, environment-driven application settings."""

import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_PLACEHOLDER = "development-only-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        enable_decoding=False,
    )

    APP_ENV: Literal["development", "demo", "production"] = "development"
    APP_NAME: str = Field(
        default="Patrol Pro API",
        validation_alias=AliasChoices("APP_NAME", "API_TITLE"),
    )
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./patrol_pro.db"

    JWT_SECRET_KEY: str = Field(
        default=DEVELOPMENT_JWT_PLACEHOLDER,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "SECRET_KEY"),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM", "ALGORITHM"),
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_IDLE_TIMEOUT_MINUTES: int = 30
    ACCOUNT_LOCK_MAX_FAILURES: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15
    EMPLOYEE_INVITATION_EXPIRE_HOURS: int = 72
    EXPOSE_DEVELOPMENT_INVITATION_TOKENS: bool = False

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "ALLOWED_ORIGINS"),
    )
    FRONTEND_URL: str = "http://localhost:3000"

    LOG_LEVEL: str = "INFO"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    RELOAD: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_RATE_LIMITING: bool = True
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Professional security patrol management platform"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value: Any) -> Any:
        """Accept the legacy DEBUG=release value as debug disabled."""
        if isinstance(value, str) and value.strip().lower() in {"release", "production"}:
            return False
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                parsed = [item.strip() for item in value.split(",")]
            value = parsed
        if isinstance(value, list):
            return [str(item).strip().rstrip("/") for item in value if str(item).strip()]
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL cannot be empty")
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @field_validator("LOG_LEVEL")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        if self.APP_ENV in {"demo", "production"}:
            if self.EXPOSE_DEVELOPMENT_INVITATION_TOKENS:
                raise ValueError(
                    "EXPOSE_DEVELOPMENT_INVITATION_TOKENS can only be enabled in development"
                )
            if not self.DATABASE_URL.startswith("postgresql+psycopg://"):
                raise ValueError("DATABASE_URL must use PostgreSQL when APP_ENV is demo or production")
            if (
                self.JWT_SECRET_KEY == DEVELOPMENT_JWT_PLACEHOLDER
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be a unique secret of at least 32 characters "
                    "when APP_ENV is demo or production"
                )
            if self.DEBUG:
                raise ValueError("DEBUG must be false when APP_ENV is demo or production")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS cannot contain '*' because credentials are enabled")
        return self

    @property
    def SECRET_KEY(self) -> str:
        """Backward-compatible alias for existing authentication code."""
        return self.JWT_SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        return self.CORS_ORIGINS

    @property
    def API_TITLE(self) -> str:
        return self.APP_NAME

    @property
    def expose_invitation_tokens(self) -> bool:
        return (
            self.APP_ENV == "development"
            and self.EXPOSE_DEVELOPMENT_INVITATION_TOKENS
        )

    def validate_production_safety(self) -> None:
        """Retained for callers; validation now occurs while settings load."""


@lru_cache()
def get_settings() -> Settings:
    return Settings()
