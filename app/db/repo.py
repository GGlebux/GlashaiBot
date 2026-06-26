"""Операции с БД: учётки пользователей и запись метрик."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import EventKind, EventStatus, UsageEvent, User


async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
) -> User:
    """Создаёт или обновляет пользователя (имя, last_seen)."""
    stmt = (
        pg_insert(User)
        .values(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_seen_at=func.now(),
        )
        .on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                "username": username,
                "first_name": first_name,
                "last_seen_at": func.now(),
            },
        )
    )
    await session.execute(stmt)
    await session.commit()
    # Возвращаем актуальную ORM-сущность (pg_insert — Core-конструкция).
    user = await session.get(User, telegram_id)
    assert user is not None
    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.get(User, telegram_id)


def effective_limit(user: User | None) -> int:
    if user is not None and user.custom_daily_limit is not None:
        return user.custom_daily_limit
    return settings.daily_limit


async def record_event(
    session: AsyncSession,
    *,
    user_id: int,
    kind: EventKind,
    status: EventStatus,
    duration_seconds: int = 0,
    processing_ms: int = 0,
    items_count: int = 1,
    error_code: str | None = None,
) -> None:
    session.add(
        UsageEvent(
            user_id=user_id,
            kind=kind,
            status=status,
            duration_seconds=duration_seconds,
            processing_ms=processing_ms,
            items_count=items_count,
            error_code=error_code,
        )
    )
    await session.commit()


# ------------------------------- Статистика --------------------------------

async def overview_stats(session: AsyncSession) -> dict[str, int]:
    """Сводные счётчики для дашборда админки."""
    total_users = await session.scalar(select(func.count()).select_from(User))
    blocked_users = await session.scalar(
        select(func.count()).select_from(User).where(User.is_blocked.is_(True))
    )
    total_events = await session.scalar(select(func.count()).select_from(UsageEvent))
    ok_events = await session.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.status == EventStatus.ok
        )
    )
    error_events = await session.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.status == EventStatus.error
        )
    )
    total_seconds = await session.scalar(
        select(func.coalesce(func.sum(UsageEvent.duration_seconds), 0))
    )
    return {
        "total_users": total_users or 0,
        "blocked_users": blocked_users or 0,
        "total_events": total_events or 0,
        "ok_events": ok_events or 0,
        "error_events": error_events or 0,
        "total_audio_minutes": round((total_seconds or 0) / 60),
    }


async def events_per_day(session: AsyncSession, days: int = 14) -> list[tuple[str, int]]:
    """Количество обработок по дням за последние N дней."""
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    day = func.date_trunc("day", UsageEvent.created_at)
    rows = await session.execute(
        select(day.label("d"), func.count().label("c"))
        .where(UsageEvent.created_at >= since)
        .group_by("d")
        .order_by("d")
    )
    return [(r.d.strftime("%d.%m"), r.c) for r in rows]


async def recent_users(session: AsyncSession, limit: int = 50) -> list[User]:
    rows = await session.execute(
        select(User).order_by(User.last_seen_at.desc()).limit(limit)
    )
    return list(rows.scalars().all())


# ----------------------------- Управление ----------------------------------

async def set_blocked(session: AsyncSession, telegram_id: int, blocked: bool) -> None:
    user = await session.get(User, telegram_id)
    if user is not None:
        user.is_blocked = blocked
        await session.commit()


async def set_custom_limit(
    session: AsyncSession, telegram_id: int, limit: int | None
) -> None:
    user = await session.get(User, telegram_id)
    if user is not None:
        user.custom_daily_limit = limit
        await session.commit()
