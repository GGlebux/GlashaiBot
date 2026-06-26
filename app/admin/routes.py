"""Роуты админки: вход через Telegram, дашборд, управление пользователями."""

from __future__ import annotations

import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from app.admin.auth import verify_telegram_auth
from app.config import settings
from app.db import repo
from app.db.base import SessionLocal
from app.redis_client import get_redis
from app.store import get_used_today

router = APIRouter()
templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))


def _admin_id(request: Request) -> int | None:
    aid = request.session.get("admin_id")
    if aid and settings.is_admin(int(aid)):
        return int(aid)
    return None


# --------------------------------- Вход -------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    if _admin_id(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "bot_username": request.app.state.bot_username,
            "auth_url": settings.admin_base_url.rstrip("/") + "/auth/telegram",
            "error": request.query_params.get("error"),
        },
    )


@router.get("/auth/telegram")
async def auth_telegram(request: Request):
    data = dict(request.query_params)
    user_id = verify_telegram_auth(data)
    if user_id is None:
        return RedirectResponse("/login?error=1", status_code=302)
    request.session["admin_id"] = user_id
    return RedirectResponse("/", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


# ------------------------------- Дашборд ------------------------------------

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not _admin_id(request):
        return RedirectResponse("/login", status_code=302)

    async with SessionLocal() as session:
        overview = await repo.overview_stats(session)
        per_day = await repo.events_per_day(session, days=14)
        users = await repo.recent_users(session, limit=50)

    user_rows = []
    for user in users:
        user_rows.append(
            {
                "id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "is_blocked": user.is_blocked,
                "limit": user.custom_daily_limit or settings.daily_limit,
                "custom": user.custom_daily_limit is not None,
                "used_today": await get_used_today(user.telegram_id),
                "last_seen": user.last_seen_at.strftime("%d.%m %H:%M"),
            }
        )

    health = await _health()
    max_day = max((c for _, c in per_day), default=0) or 1

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "overview": overview,
            "per_day": per_day,
            "max_day": max_day,
            "users": user_rows,
            "health": health,
            "default_limit": settings.daily_limit,
        },
    )


# --------------------------- Управление юзерами -----------------------------

@router.post("/users/{user_id}/block")
async def block_user(request: Request, user_id: int):
    if not _admin_id(request):
        return RedirectResponse("/login", status_code=302)
    async with SessionLocal() as session:
        await repo.set_blocked(session, user_id, True)
    return RedirectResponse("/", status_code=302)


@router.post("/users/{user_id}/unblock")
async def unblock_user(request: Request, user_id: int):
    if not _admin_id(request):
        return RedirectResponse("/login", status_code=302)
    async with SessionLocal() as session:
        await repo.set_blocked(session, user_id, False)
    return RedirectResponse("/", status_code=302)


@router.post("/users/{user_id}/limit")
async def set_limit(request: Request, user_id: int, limit: str = Form("")):
    if not _admin_id(request):
        return RedirectResponse("/login", status_code=302)
    value: int | None = None
    if limit.strip():
        try:
            value = max(0, int(limit))
        except ValueError:
            value = None
    async with SessionLocal() as session:
        await repo.set_custom_limit(session, user_id, value)
    return RedirectResponse("/", status_code=302)


# -------------------------------- Здоровье ----------------------------------

@router.get("/health")
async def health_liveness():
    """Лёгкая проверка для Docker healthcheck."""
    return JSONResponse({"status": "ok"})


async def _health() -> dict[str, object]:
    """Подробное состояние для дашборда."""
    status: dict[str, object] = {"redis": False, "db": False, "queue": None}
    try:
        status["redis"] = bool(await get_redis().ping())
    except Exception:  # noqa: BLE001
        status["redis"] = False
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        status["db"] = True
    except Exception:  # noqa: BLE001
        status["db"] = False
    try:
        status["queue"] = await get_redis().zcard("arq:queue")
    except Exception:  # noqa: BLE001
        status["queue"] = None
    return status
