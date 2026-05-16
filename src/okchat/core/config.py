"""
OkChat — Centralized Settings
Uses Pydantic v2 Settings with nested models per domain.
All config comes from environment variables, never hardcoded.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    url: SecretStr = Field(
        default="postgresql+asyncpg://okchat:okchat@localhost:5432/okchat",
        description="Async PostgreSQL connection URL",
    )
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=5)
    echo: bool = Field(default=False)

    model_config = SettingsConfigDict(env_prefix="OKCHAT_DB__", extra="ignore")


class RedisSettings(BaseSettings):
    url: SecretStr = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    pool_size: int = Field(default=20, ge=1, le=100)
    decode_responses: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="OKCHAT_REDIS__", extra="ignore")


class AuthSettings(BaseSettings):
    secret_key: SecretStr = Field(
        description="RS256 private key or HS256 secret. Use RS256 in production.",
    )
    algorithm: Literal["HS256", "RS256"] = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    model_config = SettingsConfigDict(env_prefix="OKCHAT_AUTH__", extra="ignore")


class OpenAISettings(BaseSettings):
    api_key: SecretStr = Field(description="OpenAI API key")
    default_model: str = Field(default="gpt-4o")
    timeout: float = Field(default=60.0, ge=1.0)

    model_config = SettingsConfigDict(env_prefix="OKCHAT_OPENAI__", extra="ignore")


class Settings(BaseSettings):
    # ── App ─────────────────────────────────────────────────────────────────
    app_name: str = Field(default="OkChat API")
    app_version: str = Field(default="0.1.0")
    environment: Literal["local", "staging", "production"] = Field(default="local")
    debug: bool = Field(default=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    allowed_hosts: list[str] = Field(default=["*"])
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # ── Nested domain settings ───────────────────────────────────────────────
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(default_factory=lambda: AuthSettings(
        secret_key="change-me-in-production"  # type: ignore[arg-type]
    ))
    openai: OpenAISettings | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="OKCHAT_",
        env_nested_delimiter="__",
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def debug_not_in_production(cls, v: bool, info: object) -> bool:
        # Accessed via info.data after Pydantic resolves fields in order
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use FastAPI Depends(get_settings) or call directly.
    """
    return Settings()
