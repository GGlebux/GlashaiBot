"""Приём голосовых и кружков. Маршрутизация обычный режим / цепочка."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import Message

from app.bot import progress, reactions, texts
from app.bot.reactions import Stage
from app.config import settings
from app.db.base import SessionLocal
from app.db.models import EventKind, EventStatus
from app.db.repo import effective_limit, record_event
from app.queue import get_arq_pool
from app.store import check_and_consume_limit, is_chain_active

router = Router(name="media")


@router.message(F.voice | F.video_note)
async def on_media(message: Message, bot: Bot, user) -> None:
    is_voice = message.voice is not None
    media = message.voice if is_voice else message.video_note
    file_id = media.file_id
    duration = media.duration or 0
    kind = EventKind.single_voice if is_voice else EventKind.single_video_note
    uid = message.from_user.id

    # 1. Слишком длинное.
    if duration > settings.max_audio_seconds:
        await message.answer(texts.TOO_LONG.format(max_min=settings.max_audio_seconds // 60))
        await _record(uid, kind, EventStatus.rejected, duration, "too_long")
        return

    # 2. Суточный лимит.
    limit = effective_limit(user)
    allowed, used = await check_and_consume_limit(uid, limit)
    if not allowed:
        await message.answer(texts.LIMIT_REACHED.format(used=used, limit=limit))
        await _record(uid, kind, EventStatus.rejected, duration, "daily_limit")
        return

    # 3. Принято — ставим реакцию и кладём задачу в очередь.
    await reactions.set_stage(bot, message.chat.id, message.message_id, Stage.accepted)
    pool = await get_arq_pool()

    if await is_chain_active(uid):
        # Прогресс цепочки ведёт общее статус-сообщение (создаётся в /begin).
        await pool.enqueue_job(
            "process_chain_item", message.chat.id, message.message_id, uid, file_id, duration
        )
    else:
        # Отдельное сообщение с прогресс-баром, которое потом станет выжимкой.
        percent, label = progress.SINGLE_STAGES["received"]
        prog_msg = await message.answer(progress.render(percent, label), parse_mode="HTML")
        await pool.enqueue_job(
            "process_single",
            message.chat.id,
            message.message_id,
            uid,
            file_id,
            duration,
            kind.value,
            prog_msg.message_id,
        )


async def _record(uid: int, kind: EventKind, status: EventStatus, duration: int, code: str) -> None:
    async with SessionLocal() as session:
        await record_event(
            session,
            user_id=uid,
            kind=kind,
            status=status,
            duration_seconds=duration,
            error_code=code,
        )
