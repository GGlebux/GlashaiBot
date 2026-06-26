"""Мидлвари бота: только личка, апсерт пользователя, проверка блокировки."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.bot import texts
from app.db.base import SessionLocal
from app.db.repo import upsert_user


class UserMiddleware(BaseMiddleware):
    """Пропускает только приватные чаты, регистрирует юзера, отсекает заблокированных."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.chat.type != "private":
            # В группах не работаем — тихо игнорируем (без спама).
            return None
        if event.from_user is None:
            return None

        async with SessionLocal() as session:
            user = await upsert_user(
                session,
                telegram_id=event.from_user.id,
                username=event.from_user.username,
                first_name=event.from_user.first_name,
            )

        if user.is_blocked:
            await event.answer(texts.BLOCKED)
            return None

        data["user"] = user
        return await handler(event, data)
