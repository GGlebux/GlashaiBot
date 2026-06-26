"""Клиент GigaChat (Сбер) — краткое содержание расшифровок."""

from __future__ import annotations

import logging

from app.config import settings
from app.services.sber_auth import SberToken, make_client

logger = logging.getLogger(__name__)

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

_token = SberToken(settings.gigachat_auth_key, settings.gigachat_scope)

SYSTEM_PROMPT = (
    "Ты — «Глашатай», ассистент, который делает краткое и точное содержание "
    "расшифрованной устной речи на русском языке. Сохраняй смысл, убирай воду и "
    "слова-паразиты. Если в тексте есть задачи, договорённости, даты или цифры — "
    "вынеси их отдельными пунктами. Отвечай только на русском, без вступлений."
)


class GigaChatError(Exception):
    pass


async def _headers() -> dict[str, str]:
    token = await _token.get()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def summarize(transcript: str, *, multi: bool = False) -> str:
    """Краткое содержание одной расшифровки или склейки нескольких (chain)."""
    if not transcript.strip():
        return ""

    if multi:
        instruction = (
            "Ниже — расшифровки нескольких голосовых сообщений подряд. "
            "Сделай одно общее связное краткое содержание всей цепочки:\n\n"
        )
    else:
        instruction = "Сделай краткое содержание этой расшифровки:\n\n"

    body = {
        "model": settings.gigachat_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction + transcript},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    async with make_client(timeout=90) as client:
        resp = await client.post(CHAT_URL, headers=await _headers(), json=body)
    if resp.status_code != 200:
        raise GigaChatError(f"chat/completions {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
