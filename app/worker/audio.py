"""Нормализация аудио в PCM s16le 16 кГц моно через ffmpeg.

И голосовые (ogg/opus), и кружки (mp4) приводим к единому формату, который ждёт
SaluteSpeech. Вход пишем во временный файл — так ffmpeg надёжно читает mp4
(контейнеру нужен seek, через pipe он капризничает).
"""

from __future__ import annotations

import asyncio
import os
import tempfile


class AudioError(Exception):
    pass


async def to_pcm16k(data: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise AudioError(err.decode(errors="ignore")[:300])
        if not out:
            raise AudioError("ffmpeg вернул пустой поток (нет аудиодорожки?)")
        return out
    finally:
        os.unlink(path)
