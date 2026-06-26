"""Настройки приложения. Читаются из переменных окружения / .env."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Telegram ---
    bot_token: str
    admin_ids: list[int] = []

    # --- Лимиты ---
    daily_limit: int = 20
    max_audio_seconds: int = 600

    # --- SaluteSpeech (STT) ---
    salute_speech_auth_key: str = ""
    salute_speech_scope: str = "SALUTE_SPEECH_PERS"

    # --- GigaChat (LLM) ---
    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"

    # --- TLS для сервисов Сбера (корневые сертификаты НУЦ Минцифры) ---
    # Путь к bundle с сертификатами Минцифры внутри контейнера.
    sber_ca_bundle: str = "/etc/ssl/certs/russian_trusted_ca.pem"
    # Можно отключить проверку TLS в dev, если нет сертификатов: SBER_VERIFY_SSL=false
    sber_verify_ssl: bool = True

    # --- PostgreSQL ---
    postgres_db: str = "glashatai"
    postgres_user: str = "glashatai"
    postgres_password: str = "change-me"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"

    # --- Админка ---
    admin_secret_key: str = "change-this-secret"
    admin_base_url: str = "http://localhost:8080"
    admin_port: int = 8080

    # --- Прочее ---
    log_level: str = "INFO"
    tz: str = "Europe/Moscow"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        """Разрешаем формат "111,222" из .env, а не только JSON-список."""
        if isinstance(value, str):
            return [int(x) for x in value.replace(" ", "").split(",") if x]
        return value

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids


settings = Settings()
