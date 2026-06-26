"""Единая настройка логирования.

Важно: контент пользователей (аудио, тексты, саммари) НЕ логируем — только
служебные события и метрики.
"""

from __future__ import annotations

import logging

from app.config import settings


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Приглушаем болтливые библиотеки.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
