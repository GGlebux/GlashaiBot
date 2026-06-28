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
    # Прогреваем локальную модель Whisper заранее, чтобы первое сообщение
    # не ждало загрузку модели в память.
    if settings.stt_backend.lower() == "whisper":
        import asyncio

        from app.services import whisper_stt

        await asyncio.to_thread(whisper_stt.warmup)
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
    # Локальный Whisper — CPU-bound и прожорлив по памяти: на слабом VPS
    # обрабатываем строго по одному. Облачный SaluteSpeech можно параллелить.
    max_jobs = 1 if settings.stt_backend.lower() == "whisper" else 4
    job_timeout = 600  # сек на задачу (запас для длинных аудио на слабом CPU)
