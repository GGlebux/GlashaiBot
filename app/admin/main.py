"""FastAPI-приложение админки.

Запуск:  uvicorn app.admin.main:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging

from aiogram import Bot
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.admin.routes import router
from app.config import settings
from app.db.init import init_models
from app.logging import setup_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Глашатай — админка", docs_url=None, redoc_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.admin_secret_key,
        same_site="lax",
    )
    app.include_router(router)
    app.state.bot_username = None

    @app.on_event("startup")
    async def _startup() -> None:
        await init_models()
        # Узнаём username бота — он нужен для Telegram Login Widget.
        bot = Bot(token=settings.bot_token)
        try:
            me = await bot.get_me()
            app.state.bot_username = me.username
            logger.info("Админка готова, бот @%s", me.username)
        except Exception:  # noqa: BLE001
            logger.warning("Не удалось получить username бота для виджета входа")
        finally:
            await bot.session.close()

    return app


app = create_app()
