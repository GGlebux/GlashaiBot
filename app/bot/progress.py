"""Прогресс-бар и живые статус-сообщения.

Бар рисуем символами ▰/▱ в моноширинном <code>, чтобы сегменты ровно стояли.
Сообщение редактируем по стадиям (обычный режим) или «подбрасываем» вниз
удалением+пересылкой, чтобы оно всегда было последним (режим цепочки).
"""

from __future__ import annotations

import logging

from aiogram import Bot

logger = logging.getLogger(__name__)

# Стадии обычного режима: процент + подпись.
SINGLE_STAGES: dict[str, tuple[int, str]] = {
    "received": (8, "🎧 Принял голосовое"),
    "download": (25, "📥 Скачиваю аудио"),
    "transcribe": (55, "✍️ Распознаю речь"),
    "summarize": (85, "🧠 Готовлю выжимку"),
}


def bar(percent: int, width: int = 12) -> str:
    percent = max(0, min(100, int(percent)))
    filled = round(percent / 100 * width)
    return "▰" * filled + "▱" * (width - filled) + f"  {percent}%"


def render(percent: int, label: str) -> str:
    return f"{label}\n<code>{bar(percent)}</code>"


async def edit_stage(bot: Bot, chat_id: int, msg_id: int, stage: str) -> None:
    percent, label = SINGLE_STAGES[stage]
    await edit_text(bot, chat_id, msg_id, render(percent, label))


async def edit_text(bot: Bot, chat_id: int, msg_id: int, text: str) -> None:
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=msg_id,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("edit_message_text не удался: %s", exc)


async def bump(bot: Bot, chat_id: int, old_msg_id: int | None, text: str) -> int:
    """Удаляет старое статус-сообщение и шлёт новое в самый низ. Возвращает новый id."""
    if old_msg_id:
        try:
            await bot.delete_message(chat_id, old_msg_id)
        except Exception:  # noqa: BLE001
            pass
    msg = await bot.send_message(
        chat_id, text, parse_mode="HTML", disable_web_page_preview=True
    )
    return msg.message_id
