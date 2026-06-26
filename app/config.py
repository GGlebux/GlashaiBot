"""Настройки приложения. Читаются из переменных окружения / .env."""

from __future__ import annotations

import base64

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
    # Список id админов строкой "111,222" — парсим в admin_id_list (см. ниже).
    admin_ids: str = ""

    # --- Лимиты ---
    daily_limit: int = 20
    max_audio_seconds: int = 600

    # --- SaluteSpeech (STT) ---
    # Либо готовый Authorization key (Base64), либо пара client_id + client_secret.
    salute_speech_auth_key: str = ""
    salute_speech_client_id: str = ""
    salute_speech_client_secret: str = ""
    salute_speech_scope: str = "SALUTE_SPEECH_PERS"

    # --- GigaChat (LLM) ---
    gigachat_auth_key: str = ""
    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat"
    # Запасная модель: если у основной кончился лимит/ошибка — повторим на ней.
    # Пусто — без подмены. По умолчанию падаем на бюджетную GigaChat (Lite).
    gigachat_fallback_model: str = "GigaChat"

    # --- Выбор движка распознавания речи (STT) ---
    # whisper       — локальный faster-whisper (бесплатно, без квот);
    # salutespeech  — облако Сбера (нужен подключённый пакет).
    stt_backend: str = "whisper"
    # Модель Whisper: tiny | base | small | medium | large-v3.
    # 1 ГБ → tiny/base; 2 ГБ → small (баланс качества и памяти).
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = "ru"

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

    @property
    def admin_id_list(self) -> list[int]:
        """Парсит "111,222" в список id админов."""
        return [int(x) for x in self.admin_ids.replace(" ", "").split(",") if x.strip()]

    @staticmethod
    def _basic_key(auth_key: str, client_id: str, client_secret: str) -> str:
        """Готовый Authorization key или Base64(client_id:client_secret)."""
        if auth_key.strip():
            return auth_key.strip()
        if client_id and client_secret:
            raw = f"{client_id.strip()}:{client_secret.strip()}".encode()
            return base64.b64encode(raw).decode()
        return ""

    @property
    def salute_basic_key(self) -> str:
        return self._basic_key(
            self.salute_speech_auth_key,
            self.salute_speech_client_id,
            self.salute_speech_client_secret,
        )

    @property
    def gigachat_basic_key(self) -> str:
        return self._basic_key(
            self.gigachat_auth_key,
            self.gigachat_client_id,
            self.gigachat_client_secret,
        )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_id_list


settings = Settings()
