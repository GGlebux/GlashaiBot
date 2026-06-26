"""ORM-модели. Храним ТОЛЬКО метрики — никакого контента пользователей.

- `User`     — учётка для лимитов и управления (id, username, блокировка).
- `UsageEvent` — обезличенное событие обработки (тип, статус, длительность, тайминг).
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EventKind(str, enum.Enum):
    single_voice = "single_voice"
    single_video_note = "single_video_note"
    chain = "chain"


class EventStatus(str, enum.Enum):
    ok = "ok"
    error = "error"
    rejected = "rejected"  # отклонено лимитом / слишком длинное и т.п.


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Индивидуальный лимит (переопределяет глобальный DAILY_LIMIT). NULL — глобальный.
    custom_daily_limit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    events: Mapped[list["UsageEvent"]] = relationship(back_populates="user")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[EventKind] = mapped_column(Enum(EventKind, name="event_kind"), nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"), nullable=False
    )
    # Длительность исходного аудио в секундах (для статистики; не контент).
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Сколько суммарно заняла обработка (STT+LLM), мс.
    processing_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Для цепочек — сколько сообщений вошло в саммари.
    items_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_usage_events_created_at", "created_at"),
        Index("ix_usage_events_user_created", "user_id", "created_at"),
    )
