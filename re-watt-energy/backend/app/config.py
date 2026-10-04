from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Re-Watt Energy"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite:///./rewatt.db"
    auto_create_schema: bool = True

    secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    expose_verification_codes: bool = False

    platform_fee_percent: float = 5.0
    currency: str = "KES"

    admin_email: str = ""
    admin_password: str = ""
    admin_name: str = "Platform Admin"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0

    ai_service_url: str = "http://127.0.0.1:8001"
    ai_service_api_key: str = ""
    ai_service_timeout_seconds: float = 20.0

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg3_driver(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def ai_enabled(self) -> bool:
        return bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
