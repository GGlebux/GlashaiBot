"""Локальный STT через faster-whisper.

Принимает PCM s16le 16 кГц моно (его готовит воркер через ffmpeg), отдаёт текст.
Тяжёлая синхронная работа выносится в поток, чтобы не блокировать event loop.
Модель грузится один раз (ленивый синглтон).
"""

from __future__ import annotations

import asyncio
import logging

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info(
            "Загружаю модель Whisper '%s' (%s, %s)…",
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Модель Whisper готова")
    return _model


def warmup() -> None:
    """Прогрев: загрузить модель в память заранее (вызывается на старте воркера)."""
    _get_model()


def _transcribe_sync(pcm: bytes) -> str:
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    model = _get_model()
    segments, _info = model.transcribe(
        audio,
        language=settings.whisper_language,
        beam_size=1,  # жадная стратегия — быстрее на слабом CPU
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


async def transcribe(pcm_audio: bytes, duration_seconds: int) -> str:
    return await asyncio.to_thread(_transcribe_sync, pcm_audio)
