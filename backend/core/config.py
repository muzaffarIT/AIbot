from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    debug: bool = True

    bot_token: str | None = None
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_base_url: str = "http://localhost:8000"

    postgres_url: str
    redis_url: str

    miniapp_url: str | None = None

    secret_key: str
    default_language: str = "ru"
    ai_mock_mode: bool = True
    generation_process_now: bool = True
    celery_task_always_eager: bool = False
    generation_poll_interval_seconds: int = 2
    generation_poll_attempts: int = 90
    generation_callback_base_url: str | None = None

    nano_banana_provider: str = "kie"
    kling_provider: str = "kie"
    veo_provider: str = "kie"

    kie_api_key: str | None = None
    kie_base_url: str | None = None

    nano_banana_api_key: str | None = None
    kling_api_key: str | None = None
    veo_api_key: str | None = None

    cards_provider_key: str | None = None
    cards_provider_secret: str | None = None

    payme_merchant_id: str | None = None
    payme_secret_key: str | None = None

    payment_provider: str = "stars"
    admin_ids: str = ""
    welcome_credits: int = 10
    daily_credits: int = 3
    max_free_gens_per_day: int = 5
    referral_bonus_referrer: int = 20
    referral_bonus_new_user: int = 10
    support_username: str = "khaetov_000"

    click_merchant_id: str | None = None
    click_service_id: str | None = None
    click_secret_key: str | None = None

    @field_validator("secret_key", mode="before")
    @classmethod
    def validate_secret_key(cls, value: Any) -> Any:
        if not value:
            import secrets
            return secrets.token_hex(32)
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
