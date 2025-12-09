"""Application configuration using pydantic-settings."""
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="orders-service", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )

    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/orders_db",
        description="PostgreSQL connection URL",
    )

    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    admin_secret: str = Field(
        default="change-this-secret-in-production", description="Admin API secret"
    )
    payment_webhook_secret: str = Field(
        default="change-this-webhook-secret", description="Payment webhook HMAC secret"
    )

    rate_limit_orders_per_minute: int = Field(
        default=5, description="Max orders per minute per user/IP"
    )

    outbox_worker_interval_seconds: int = Field(
        default=5, description="Outbox worker polling interval"
    )
    outbox_max_attempts: int = Field(default=5, description="Max retry attempts for outbox events")
    outbox_retry_base_delay_seconds: int = Field(
        default=1, description="Base delay for exponential backoff"
    )

    fake_payment_enabled: bool = Field(default=True, description="Enable fake payment service")
    fake_payment_success_rate: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Success rate for fake payments (0.0-1.0)"
    )


settings = Settings()

