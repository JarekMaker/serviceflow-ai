from functools import lru_cache

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    project_name: str = "ServiceFlow AI"
    environment: str = "local"
    backend_cors_origins: str = "http://localhost:5173,http://localhost"
    database_url: str = "sqlite+aiosqlite:///./serviceflow.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "dev-secret"
    jwt_expire_minutes: int = 60
    admin_email: str = "admin@serviceflow.local"
    admin_password: str = "Admin123!ChangeMe"
    ai_provider: str = "mock"
    ai_confidence_threshold: float = 0.75
    anthropic_api_key: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_base_url: AnyHttpUrl | None = None
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "serviceflow@local.test"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "serviceflow-attachments"
    n8n_webhook_secret: str = "dev-webhook-secret"
    max_attachment_mb: int = 10
    allowed_attachment_types: str = "image/jpeg,image/png,application/pdf,text/plain"
    duplicate_window_hours: int = 24
    rate_limit_per_minute: int = 30

    @field_validator(
        "anthropic_api_key",
        "openai_compatible_api_key",
        "openai_compatible_base_url",
        "smtp_username",
        "smtp_password",
        "telegram_bot_token",
        "telegram_chat_id",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def allowed_content_types(self) -> set[str]:
        return {item.strip() for item in self.allowed_attachment_types.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
