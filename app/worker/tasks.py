"""Задачи воркера: распознавание и краткое содержание.

Обычный режим ведёт живой прогресс-бар в одном сообщении, затем превращает его в
выжимку (тезисы + тон), а полный текст шлёт отдельным сообщением в конце.
Цепочка держит одно статус-сообщение, «подбрасывая» его вниз по мере приёма.
Контент пользователя нигде не сохраняется — только обезличенные метрики.
"""

from __future__ import annotations

import io
import logging
import time

from aiogram import Bot

from app.bot import progress, texts
from app.bot.reactions import Stage, set_stage
from app.bot.utils import send_html_chunks
from app.db.base import SessionLocal
from app.db.models import EventKind, EventStatus
from app.db.repo import record_event
from app.services.gigachat import summarize_rich
from app.services.stt import transcribe
from app.store import (
    add_chain_text,
    chain_count,
    get_chain_progress,
    pop_chain,
    set_chain_progress,
)
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
    progress_msg_id: int,
) -> None:
    bot: Bot = ctx["bot"]
    kind = EventKind(kind_str)
    started = time.monotonic()
    status = EventStatus.ok
    error_code: str | None = None
    try:
        await progress.edit_stage(bot, chat_id, progress_msg_id, "download")
        audio = await _download(bot, file_id)

        await progress.edit_stage(bot, chat_id, progress_msg_id, "transcribe")
        pcm = await to_pcm16k(audio)
        transcript = await transcribe(pcm, duration)

        if transcript:
            await progress.edit_stage(bot, chat_id, progress_msg_id, "summarize")
            points, tone = await summarize_rich(transcript)
            # Прогресс-сообщение превращаем в выжимку + тон…
            await progress.edit_text(
                bot, chat_id, progress_msg_id, texts.format_single_summary(points, tone)
            )
            # …а полный текст шлём отдельным сообщением в конце.
            await send_html_chunks(bot, chat_id, texts.format_transcript(transcript))
        else:
            await progress.edit_text(
                bot,
                chat_id,
                progress_msg_id,
                "🤔 Не удалось распознать речь — возможно, тишина или шум.",
            )

        await set_stage(bot, chat_id, message_id, Stage.done)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка обработки single для user=%s", user_id)
        status = EventStatus.error
        error_code = type(exc).__name__
        await set_stage(bot, chat_id, message_id, Stage.error)
        await progress.edit_text(bot, chat_id, progress_msg_id, texts.ERROR_GENERIC)
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
    """Распознаёт одно сообщение цепочки, копит текст и обновляет статус внизу."""
    bot: Bot = ctx["bot"]
    try:
        await set_stage(bot, chat_id, message_id, Stage.transcribing)
        audio = await _download(bot, file_id)
        pcm = await to_pcm16k(audio)
        transcript = await transcribe(pcm, duration)
        if transcript:
            await add_chain_text(user_id, transcript, duration)
        await set_stage(bot, chat_id, message_id, Stage.captured)

        # Подбрасываем статус-сообщение вниз с новым счётчиком.
        count = await chain_count(user_id)
        prog = await get_chain_progress(user_id)
        old_msg = prog[1] if prog else None
        new_id = await progress.bump(bot, chat_id, old_msg, texts.chain_progress(count))
        await set_chain_progress(user_id, chat_id, new_id)
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
    prog = await get_chain_progress(user_id)
    old_msg = prog[1] if prog else None
    items, total_duration = await pop_chain(user_id)

    if not items:
        await progress.bump(bot, chat_id, old_msg, texts.CHAIN_EMPTY)
        return

    # Подбрасываем статус вниз (под команду /end) с баром «собираю».
    status_id = await progress.bump(
        bot, chat_id, old_msg, progress.render(60, "🧠 Собираю общую выжимку")
    )
    started = time.monotonic()
    status = EventStatus.ok
    error_code: str | None = None
    try:
        combined = "\n\n".join(f"{i + 1}. {text}" for i, text in enumerate(items))
        points, tone = await summarize_rich(combined)
        body = texts.format_chain_summary(points, tone, len(items))
        await progress.edit_text(bot, chat_id, status_id, body)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка финализации цепочки для user=%s", user_id)
        status = EventStatus.error
        error_code = type(exc).__name__
        await progress.edit_text(bot, chat_id, status_id, texts.ERROR_GENERIC)
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
