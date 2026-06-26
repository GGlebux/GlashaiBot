"""Задачи воркера: распознавание и краткое содержание.

Каждая задача обновляет реакцию-статус под исходным сообщением, шлёт результат
и пишет обезличенную метрику в БД. Контент пользователя нигде не сохраняется.
"""

from __future__ import annotations

import io
import logging
import time

from aiogram import Bot

from app.bot import texts
from app.bot.reactions import Stage, set_stage
from app.bot.utils import send_html_chunks
from app.db.base import SessionLocal
from app.db.models import EventKind, EventStatus
from app.db.repo import record_event
from app.services.gigachat import summarize
from app.services.stt import transcribe
from app.store import add_chain_text, pop_chain
from app.worker.audio import to_pcm16k

logger = logging.getLogger(__name__)


async def _download(bot: Bot, file_id: str) -> bytes:
    buf = io.BytesIO()
    await bot.download(file_id, destination=buf)
    return buf.getvalue()


async def _save_event(**kwargs) -> None:
    async with SessionLocal() as session:
        await record_event(session, **kwargs)


# ---------------------------- Обычный режим ---------------------------------

async def process_single(
    ctx: dict,
    chat_id: int,
    message_id: int,
    user_id: int,
    file_id: str,
    duration: int,
    kind_str: str,
) -> None:
    bot: Bot = ctx["bot"]
    kind = EventKind(kind_str)
    started = time.monotonic()
    status = EventStatus.ok
    error_code: str | None = None
    try:
        await set_stage(bot, chat_id, message_id, Stage.transcribing)
        audio = await _download(bot, file_id)
        pcm = await to_pcm16k(audio)
        transcript = await transcribe(pcm, duration)

        if transcript:
            summary = await summarize(transcript)
            body = texts.format_single_result(transcript, summary)
        else:
            body = "🤔 Не удалось распознать речь — возможно, тишина или шум."

        await send_html_chunks(bot, chat_id, body, reply_to_message_id=message_id)
        await set_stage(bot, chat_id, message_id, Stage.done)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка обработки single для user=%s", user_id)
        status = EventStatus.error
        error_code = type(exc).__name__
        await set_stage(bot, chat_id, message_id, Stage.error)
        await bot.send_message(chat_id, texts.ERROR_GENERIC, reply_to_message_id=message_id)
    finally:
        await _save_event(
            user_id=user_id,
            kind=kind,
            status=status,
            duration_seconds=duration,
            processing_ms=int((time.monotonic() - started) * 1000),
            error_code=error_code,
        )


# ------------------------------- Цепочка ------------------------------------

async def process_chain_item(
    ctx: dict,
    chat_id: int,
    message_id: int,
    user_id: int,
    file_id: str,
    duration: int,
) -> None:
    """Распознаёт одно сообщение цепочки и копит текст в сессии (без саммари)."""
    bot: Bot = ctx["bot"]
    try:
        await set_stage(bot, chat_id, message_id, Stage.transcribing)
        audio = await _download(bot, file_id)
        pcm = await to_pcm16k(audio)
        transcript = await transcribe(pcm, duration)
        if transcript:
            await add_chain_text(user_id, transcript, duration)
        await set_stage(bot, chat_id, message_id, Stage.captured)
    except Exception:  # noqa: BLE001
        logger.exception("Ошибка обработки chain-item для user=%s", user_id)
        await set_stage(bot, chat_id, message_id, Stage.error)


async def process_chain_finalize(
    ctx: dict,
    chat_id: int,
    message_id: int,
    user_id: int,
) -> None:
    """Собирает все тексты цепочки и делает одно общее краткое содержание."""
    bot: Bot = ctx["bot"]
    items, total_duration = await pop_chain(user_id)
    if not items:
        await set_stage(bot, chat_id, message_id, Stage.error)
        await bot.send_message(chat_id, texts.CHAIN_EMPTY)
        return

    # Показываем, что собираем общее краткое содержание.
    await set_stage(bot, chat_id, message_id, Stage.summarizing)
    started = time.monotonic()
    status = EventStatus.ok
    error_code: str | None = None
    try:
        combined = "\n\n".join(f"{i + 1}. {text}" for i, text in enumerate(items))
        summary = await summarize(combined, multi=True)
        body = texts.format_chain_result(summary, len(items))
        await send_html_chunks(bot, chat_id, body, reply_to_message_id=message_id)
        await set_stage(bot, chat_id, message_id, Stage.done)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка финализации цепочки для user=%s", user_id)
        status = EventStatus.error
        error_code = type(exc).__name__
        await set_stage(bot, chat_id, message_id, Stage.error)
        await bot.send_message(chat_id, texts.ERROR_GENERIC)
    finally:
        await _save_event(
            user_id=user_id,
            kind=EventKind.chain,
            status=status,
            duration_seconds=total_duration,
            processing_ms=int((time.monotonic() - started) * 1000),
            items_count=len(items),
            error_code=error_code,
        )
