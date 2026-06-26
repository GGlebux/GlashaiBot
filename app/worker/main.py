"""Настройки воркера arq.

Запуск:  arq app.worker.main.WorkerSettings
"""

from __future__ import annotations

import logging

from aiogram import Bot

from app.config import settings
from app.db.init import init_models
from app.logging import setup_logging
from app.queue import redis_settings
from app.worker.tasks import (
    process_chain_finalize,
    process_chain_item,
    process_single,
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    setup_logging()
    await init_models()
    ctx["bot"] = Bot(token=settings.bot_token)
    logger.info("Воркер Глашатая запущен 📯")


async def shutdown(ctx: dict) -> None:
    bot: Bot = ctx.get("bot")
    if bot is not None:
        await bot.session.close()


class WorkerSettings:
    functions = [process_single, process_chain_item, process_chain_finalize]
    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    # На слабом VPS и бесплатной квоте Сбера ограничиваем параллелизм.
    max_jobs = 4
    job_timeout = 300  # сек на одну задачу (учитывает async-распознавание длинных аудио)
