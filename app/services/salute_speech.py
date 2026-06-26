"""Клиент SaluteSpeech (Сбер) — распознавание речи (STT).

Работаем с нормализованным аудио PCM s16le, 16 кГц, моно (его готовит воркер
через ffmpeg). Для короткого аудио — синхронный `speech:recognize`, для длинного
— асинхронный путь (upload → async_recognize → poll → download).

Документация форматов может меняться — если SaluteSpeech вернёт неожиданную
структуру, парсинг сделан максимально терпимым.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.services.sber_auth import SberToken, make_client

logger = logging.getLogger(__name__)

BASE = "https://smartspeech.sber.ru/rest/v1"

# Параметры нормализованного аудио, которое отдаёт воркер.
PCM_SAMPLE_RATE = 16000
PCM_CONTENT_TYPE = f"audio/x-pcm;bit=16;rate={PCM_SAMPLE_RATE}"
PCM_ENCODING = "PCM_S16LE"

# Порог, после которого уходим в асинхронное распознавание (сек).
SYNC_LIMIT_SECONDS = 55

_token = SberToken(settings.salute_basic_key, settings.salute_speech_scope)


class SaluteSpeechError(Exception):
    pass


async def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    token = await _token.get()
    headers = {"Authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    return headers


async def transcribe(pcm_audio: bytes, duration_seconds: int, language: str = "ru-RU") -> str:
    """Главная точка входа: выбирает sync/async по длительности."""
    if duration_seconds <= SYNC_LIMIT_SECONDS:
        return await _recognize_sync(pcm_audio, language)
    return await _recognize_async(pcm_audio, language)


async def _recognize_sync(pcm_audio: bytes, language: str) -> str:
    headers = await _headers({"Content-Type": PCM_CONTENT_TYPE})
    params = {"language": language}
    async with make_client(timeout=90) as client:
        resp = await client.post(
            f"{BASE}/speech:recognize", headers=headers, params=params, content=pcm_audio
        )
    if resp.status_code != 200:
        raise SaluteSpeechError(f"speech:recognize {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    # Ответ: {"result": ["сегмент1", "сегмент2", ...], "status": 200}
    return " ".join(part for part in data.get("result", []) if part).strip()


async def _recognize_async(pcm_audio: bytes, language: str) -> str:
    async with make_client(timeout=180) as client:
        # 1. Загрузка файла.
        up_headers = await _headers({"Content-Type": "application/octet-stream"})
        up = await client.post(f"{BASE}/data:upload", headers=up_headers, content=pcm_audio)
        if up.status_code != 200:
            raise SaluteSpeechError(f"data:upload {up.status_code}: {up.text[:300]}")
        request_file_id = up.json()["result"]["request_file_id"]

        # 2. Запуск задачи распознавания.
        body = {
            "options": {
                "language": language,
                "audio_encoding": PCM_ENCODING,
                "sample_rate": PCM_SAMPLE_RATE,
                "channels_count": 1,
            },
            "request_file_id": request_file_id,
        }
        js_headers = await _headers({"Content-Type": "application/json"})
        start = await client.post(
            f"{BASE}/speech:async_recognize", headers=js_headers, json=body
        )
        if start.status_code != 200:
            raise SaluteSpeechError(f"async_recognize {start.status_code}: {start.text[:300]}")
        task_id = start.json()["result"]["id"]

        # 3. Поллинг статуса.
        response_file_id = await _wait_task(client, task_id)

        # 4. Скачивание результата.
        dl_headers = await _headers()
        dl = await client.get(
            f"{BASE}/data:download",
            headers=dl_headers,
            params={"response_file_id": response_file_id},
        )
        if dl.status_code != 200:
            raise SaluteSpeechError(f"data:download {dl.status_code}: {dl.text[:300]}")
        return _parse_async_result(dl.json())


async def _wait_task(client, task_id: str, attempts: int = 60, delay: float = 3.0) -> str:
    headers = await _headers()
    for _ in range(attempts):
        resp = await client.get(f"{BASE}/task:get", headers=headers, params={"id": task_id})
        if resp.status_code != 200:
            raise SaluteSpeechError(f"task:get {resp.status_code}: {resp.text[:300]}")
        result = resp.json().get("result", {})
        status = result.get("status")
        if status == "DONE":
            return result["response_file_id"]
        if status in {"ERROR", "CANCELED"}:
            raise SaluteSpeechError(f"Задача распознавания завершилась статусом {status}")
        await asyncio.sleep(delay)
    raise SaluteSpeechError("Таймаут ожидания асинхронного распознавания")


def _parse_async_result(data: object) -> str:
    """Терпимо вытаскиваем текст из результата async-распознавания."""
    texts: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key in ("normalized_text", "text"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    texts.append(value.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return " ".join(texts).strip()
