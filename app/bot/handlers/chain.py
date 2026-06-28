"""Команды режима цепочки: /begin, /end, /cancel."""

from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot import texts
from app.queue import get_arq_pool
from app.store import (
    get_chain_progress,
    is_chain_active,
    pop_chain,
    set_chain_progress,
    start_chain,
)

router = Router(name="chain")


@router.message(Command("begin"))
async def cmd_begin(message: Message) -> None:
    uid = message.from_user.id
    if await is_chain_active(uid):
        await message.answer(texts.CHAIN_ALREADY, parse_mode="HTML")
        return
    await start_chain(uid)
    # Единое статус-сообщение цепочки — его воркер будет «подбрасывать» вниз.
    prog = await message.answer(texts.chain_progress(0), parse_mode="HTML")
    await set_chain_progress(uid, message.chat.id, prog.message_id)


@router.message(Command("end"))
async def cmd_end(message: Message) -> None:
    uid = message.from_user.id
    if not await is_chain_active(uid):
        await message.answer(texts.CHAIN_NOT_ACTIVE)
        return
    pool = await get_arq_pool()
    await pool.enqueue_job("process_chain_finalize", message.chat.id, message.message_id, uid)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, bot: Bot) -> None:
    uid = message.from_user.id
    if not await is_chain_active(uid):
        await message.answer(texts.CHAIN_NOT_ACTIVE)
        return
    prog = await get_chain_progress(uid)
    await pop_chain(uid)  # выбрасываем накопленное
    if prog:
        try:
            await bot.delete_message(prog[0], prog[1])
        except Exception:  # noqa: BLE001
            pass
    await message.answer(texts.CHAIN_CANCELLED)
