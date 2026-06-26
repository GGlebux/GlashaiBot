"""Конечный автомат эмодзи-реакций под сообщением пользователя.

Telegram разрешает ботам только фиксированный набор эмодзи-реакций, поэтому
используем заведомо допустимые. Каждая установка реакции заменяет предыдущую,
что и даёт эффект прогресса.
"""

from __future__ import annotations

import enum
import logging

from aiogram import Bot
from aiogram.types import ReactionTypeEmoji

logger = logging.getLogger(__name__)


class Stage(str, enum.Enum):
    accepted = "👀"      # принял в работу
    transcribing = "✍️"  # распознаю
    captured = "👍"      # фрагмент цепочки подхвачен
    done = "🎉"          # готово
    error = "⚡"          # ошибка


async def set_stage(bot: Bot, chat_id: int, message_id: int, stage: Stage) -> None:
    """Ставит реакцию-статус. Ошибки молча проглатываем (например, старое сообщение)."""
    try:
        await bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[ReactionTypeEmoji(emoji=stage.value)],
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("Не удалось поставить реакцию %s: %s", stage.value, exc)
