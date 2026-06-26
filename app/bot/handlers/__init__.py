"""Роутеры бота."""

from aiogram import Router

from app.bot.handlers import chain, common, media


def get_router() -> Router:
    root = Router()
    root.include_router(common.router)
    root.include_router(chain.router)
    root.include_router(media.router)
    return root
