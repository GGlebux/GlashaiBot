"""Диспетчер распознавания речи: выбирает движок по настройке STT_BACKEND."""

from __future__ import annotations

from app.config import settings


async def transcribe(pcm_audio: bytes, duration_seconds: int) -> str:
    """Единая точка входа STT для воркера."""
    if settings.stt_backend.lower() == "salutespeech":
        from app.services import salute_speech

        return await salute_speech.transcribe(pcm_audio, duration_seconds)

    # По умолчанию — локальный Whisper.
    from app.services import whisper_stt

    return await whisper_stt.transcribe(pcm_audio, duration_seconds)
