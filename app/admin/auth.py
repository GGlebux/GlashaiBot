"""Проверка авторизации через Telegram Login Widget.

Алгоритм (по документации Telegram):
  secret = sha256(bot_token)
  hash   = HMAC_SHA256(data_check_string, secret)
data_check_string — все поля кроме hash, отсортированные, в виде "k=v\n".
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.config import settings

AUTH_MAX_AGE = 86400  # сутки


def verify_telegram_auth(data: dict[str, str]) -> int | None:
    """Возвращает telegram-id, если подпись валидна и юзер — админ, иначе None."""
    received_hash = data.get("hash")
    if not received_hash:
        return None

    check_string = "\n".join(
        f"{key}={data[key]}" for key in sorted(data) if key != "hash"
    )
    secret = hashlib.sha256(settings.bot_token.encode()).digest()
    calculated = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None

    try:
        if time.time() - int(data.get("auth_date", "0")) > AUTH_MAX_AGE:
            return None
        user_id = int(data["id"])
    except (ValueError, KeyError):
        return None

    if not settings.is_admin(user_id):
        return None
    return user_id
