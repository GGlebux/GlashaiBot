"""Идемпотентное создание таблиц при старте сервисов.

Для простоты «одной командой» таблицы создаются автоматически. Схема простая
(две таблицы метрик), миграции пока не требуются.
"""

from __future__ import annotations

from app.db import models  # noqa: F401  — регистрирует модели в metadata
from app.db.base import Base, engine


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
