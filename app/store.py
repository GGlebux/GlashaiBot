"""Redis-хранилище runtime-состояния: суточные лимиты и сессии режима /begin.

Используется и ботом, и воркером. Постоянные данные тут не лежат — только TTL-ключи.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from app.config import settings
from app.redis_client import get_redis

_TZ = ZoneInfo(settings.tz)
CHAIN_TTL = 3600  # сессия /begin живёт час


# ----------------------------- Суточные лимиты ------------------------------

def _today_key() -> str:
    return dt.datetime.now(_TZ).strftime("%Y%m%d")


def _seconds_to_midnight() -> int:
    now = dt.datetime.now(_TZ)
    tomorrow = (now + dt.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(60, int((tomorrow - now).total_seconds()))


async def check_and_consume_limit(user_id: int, limit: int) -> tuple[bool, int]:
    """Проверяет суточный лимит и при успехе увеличивает счётчик.

    Возвращает (разрешено, сколько_использовано_после).
    """
    redis = get_redis()
    key = f"limit:{user_id}:{_today_key()}"
    used = int(await redis.get(key) or 0)
    if used >= limit:
        return False, used
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, _seconds_to_midnight())
    return True, used


async def get_used_today(user_id: int) -> int:
    redis = get_redis()
    return int(await redis.get(f"limit:{user_id}:{_today_key()}") or 0)


# ------------------------- Сессии режима цепочки ----------------------------

def _chain_active_key(uid: int) -> str:
    return f"chain:active:{uid}"


def _chain_texts_key(uid: int) -> str:
    return f"chain:texts:{uid}"


def _chain_dur_key(uid: int) -> str:
    return f"chain:dur:{uid}"


async def start_chain(uid: int) -> None:
    redis = get_redis()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.delete(_chain_texts_key(uid), _chain_dur_key(uid))
        pipe.set(_chain_active_key(uid), "1", ex=CHAIN_TTL)
        await pipe.execute()


async def is_chain_active(uid: int) -> bool:
    redis = get_redis()
    return bool(await redis.exists(_chain_active_key(uid)))


async def add_chain_text(uid: int, text: str, duration: int) -> None:
    """Добавляет распознанный фрагмент в текущую сессию цепочки."""
    redis = get_redis()
    async with redis.pipeline(transaction=True) as pipe:
        pipe.rpush(_chain_texts_key(uid), text)
        pipe.incrby(_chain_dur_key(uid), duration)
        # Продлеваем жизнь сессии, пока юзер активно кидает сообщения.
        pipe.expire(_chain_active_key(uid), CHAIN_TTL)
        pipe.expire(_chain_texts_key(uid), CHAIN_TTL)
        pipe.expire(_chain_dur_key(uid), CHAIN_TTL)
        await pipe.execute()


async def pop_chain(uid: int) -> tuple[list[str], int]:
    """Забирает все тексты цепочки и закрывает сессию."""
    redis = get_redis()
    texts = await redis.lrange(_chain_texts_key(uid), 0, -1)
    duration = int(await redis.get(_chain_dur_key(uid)) or 0)
    await redis.delete(
        _chain_active_key(uid), _chain_texts_key(uid), _chain_dur_key(uid)
    )
    return texts, duration
