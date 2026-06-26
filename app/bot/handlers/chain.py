"""Команды режима цепочки: /begin, /end, /cancel."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot import texts
from app.queue import get_arq_pool
from app.store import is_chain_active, pop_chain, start_chain

router = Router(name="chain")


@router.message(Command("begin"))
async def cmd_begin(message: Message) -> None:
    uid = message.from_user.id
    if await is_chain_active(uid):
        await message.answer(texts.CHAIN_ALREADY, parse_mode="HTML")
        return
    await start_chain(uid)
    await message.answer(texts.CHAIN_STARTED, parse_mode="HTML")


@router.message(Command("end"))
async def cmd_end(message: Message) -> None:
    uid = message.from_user.id
    if not await is_chain_active(uid):
        await message.answer(texts.CHAIN_NOT_ACTIVE)
        return
    await message.answer(texts.CHAIN_FINALIZING)
    pool = await get_arq_pool()
    await pool.enqueue_job("process_chain_finalize", message.chat.id, message.message_id, uid)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    uid = message.from_user.id
    if await is_chain_active(uid):
        await pop_chain(uid)  # просто выбрасываем накопленное
        await message.answer(texts.CHAIN_CANCELLED)
    else:
        await message.answer(texts.CHAIN_NOT_ACTIVE)
