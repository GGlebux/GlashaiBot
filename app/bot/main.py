"""Точка входа бота (aiogram, long polling).

Запуск:  python -m app.bot.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from app.bot.handlers import get_router
from app.bot.middlewares import UserMiddleware
from app.config import settings
from app.db.init import init_models
from app.logging import setup_logging

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="О боте"),
    BotCommand(command="help", description="Как пользоваться"),
    BotCommand(command="begin", description="Начать цепочку сообщений"),
    BotCommand(command="end", description="Завершить цепочку и получить саммари"),
    BotCommand(command="cancel", description="Отменить цепочку"),
]


async def main() -> None:
    setup_logging()
    await init_models()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.message.middleware(UserMiddleware())
    dp.include_router(get_router())

    await bot.set_my_commands(COMMANDS)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Глашатай запущен 📯")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
