"""Клиент GigaChat (Сбер) — краткое содержание расшифровок."""

from __future__ import annotations

import json
import logging

from app.config import settings
from app.services.sber_auth import SberToken, make_client

logger = logging.getLogger(__name__)

CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

_token = SberToken(settings.gigachat_basic_key, settings.gigachat_scope)

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


async def _complete(messages: list[dict], model: str) -> str:
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    async with make_client(timeout=90) as client:
        resp = await client.post(CHAT_URL, headers=await _headers(), json=body)
    if resp.status_code != 200:
        raise GigaChatError(f"chat/completions [{model}] {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"].strip()


async def summarize(transcript: str, *, multi: bool = False) -> str:
    """Краткое содержание одной расшифровки или склейки нескольких (chain).

    Если у основной модели ошибка/исчерпан лимит — повторяем на запасной.
    """
    if not transcript.strip():
        return ""

    if multi:
        instruction = (
            "Ниже — расшифровки нескольких голосовых сообщений подряд. "
            "Сделай одно общее связное краткое содержание всей цепочки:\n\n"
        )
    else:
        instruction = "Сделай краткое содержание этой расшифровки:\n\n"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": instruction + transcript},
    ]

    return await _complete_with_fallback(messages)


async def _complete_with_fallback(messages: list[dict]) -> str:
    model = settings.gigachat_model
    try:
        return await _complete(messages, model)
    except GigaChatError as exc:
        fallback = settings.gigachat_fallback_model
        if fallback and fallback != model:
            logger.warning(
                "GigaChat %s не ответил (%s) — пробую запасную модель %s",
                model, exc, fallback,
            )
            return await _complete(messages, fallback)
        raise


RICH_INSTRUCTION = (
    "Проанализируй расшифровку устной речи и верни СТРОГО валидный JSON без "
    "markdown и пояснений, по схеме:\n"
    '{"points": ["тезис", "..."], "tone": "тон/стиль общения"}\n'
    "Требования: 2–6 тезисов, каждый начинается с подходящего по смыслу эмодзи и "
    "пробела; кратко, по-русски, без воды. Поле tone — короткое словосочетание "
    "(напр.: «деловой, нейтральный» или «повседневный, дружеский»).\n\nТекст:\n"
)


async def summarize_rich(transcript: str) -> tuple[list[str], str]:
    """Возвращает (тезисы_с_эмодзи, тон). При сбое парсинга — деградирует мягко."""
    if not transcript.strip():
        return [], ""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": RICH_INSTRUCTION + transcript},
    ]
    raw = await _complete_with_fallback(messages)
    return _parse_rich(raw)


def _parse_rich(raw: str) -> tuple[list[str], str]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            points = [str(p).strip() for p in data.get("points", []) if str(p).strip()]
            tone = str(data.get("tone", "")).strip()
            if points:
                return points, tone
        except (ValueError, AttributeError):
            pass
    # Мягкая деградация: бьём ответ на строки-тезисы.
    lines = [ln.strip("•-–* ").strip() for ln in raw.splitlines() if ln.strip()]
    return (lines or [raw.strip()]), ""
