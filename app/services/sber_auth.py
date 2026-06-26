"""Общий OAuth2-доступ к сервисам Сбера (SaluteSpeech, GigaChat).

Оба API авторизуются одинаково: по `Authorization key` получаем access-токен,
который живёт ~30 минут. Здесь — кэширование токена и фабрика httpx-клиента,
доверяющего корневым сертификатам НУЦ Минцифры.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"


def _verify() -> bool | str:
    """Что передать в httpx `verify`: путь к bundle Минцифры, True или False."""
    if not settings.sber_verify_ssl:
        return False
    if settings.sber_ca_bundle and os.path.exists(settings.sber_ca_bundle):
        return settings.sber_ca_bundle
    return True


def make_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """httpx-клиент для запросов к сервисам Сбера."""
    return httpx.AsyncClient(verify=_verify(), timeout=timeout)


class SberToken:
    """Кэширующий менеджер access-токена для одного scope."""

    def __init__(self, auth_key: str, scope: str) -> None:
        self._auth_key = auth_key
        self._scope = scope
        self._token: str | None = None
        self._expires_at: float = 0.0  # epoch-секунды
        self._lock = asyncio.Lock()

    async def get(self) -> str:
        async with self._lock:
            now = time.time()
            # Обновляем заранее, за минуту до истечения.
            if self._token and now < self._expires_at - 60:
                return self._token
            await self._refresh()
            assert self._token is not None
            return self._token

    async def _refresh(self) -> None:
        if not self._auth_key:
            raise RuntimeError(
                f"Не задан Authorization key для scope={self._scope}. "
                "Проверь .env (SALUTE_SPEECH_AUTH_KEY / GIGACHAT_AUTH_KEY)."
            )
        headers = {
            "Authorization": f"Basic {self._auth_key}",
            "RqUID": str(uuid.uuid4()),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        async with make_client() as client:
            resp = await client.post(OAUTH_URL, headers=headers, data={"scope": self._scope})
            resp.raise_for_status()
            data = resp.json()
        self._token = data["access_token"]
        # expires_at приходит в миллисекундах epoch.
        self._expires_at = float(data["expires_at"]) / 1000.0
        logger.info("Получен токен Сбера (scope=%s)", self._scope)
