"""Диагностика бэкендов «Глашатай»: STT (Whisper/SaluteSpeech) + GigaChat.

Запуск (лучше в контейнере, где стоят сертификаты Минцифры и модель Whisper):
    docker run --rm --env-file .env <image> python -m app.scripts.check_api

Секреты не печатаются (только маска).
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.config import settings
from app.services import gigachat


def _mask(value: str) -> str:
    if not value:
        return "(пусто)"
    if len(value) <= 10:
        return f"(len={len(value)})"
    return f"{value[:4]}…{value[-4:]} (len={len(value)})"


def _looks_like_uuid(value: str) -> bool:
    return len(value) == 36 and len(value.split("-")) == 5


def _print_env() -> None:
    bundle = settings.sber_ca_bundle
    exists = os.path.exists(bundle) if bundle else False
    print("Окружение:")
    print(f"  STT backend         : {settings.stt_backend}")
    if settings.stt_backend.lower() == "whisper":
        print(f"  Whisper model       : {settings.whisper_model} ({settings.whisper_compute_type}, {settings.whisper_device})")
    else:
        print(f"  SaluteSpeech key    : {_mask(settings.salute_basic_key)}  scope={settings.salute_speech_scope}")
        if settings.salute_speech_auth_key and _looks_like_uuid(settings.salute_speech_auth_key):
            print("  ⚠️  SALUTE_SPEECH_AUTH_KEY похож на Client ID, а нужен Authorization key.")
    print(f"  GigaChat key        : {_mask(settings.gigachat_basic_key)}  scope={settings.gigachat_scope}  model={settings.gigachat_model}")
    print(f"  ca_bundle           : {bundle} (существует: {exists})")
    print()


async def check_stt() -> bool:
    backend = settings.stt_backend.lower()
    print(f"— STT: {backend} —")
    try:
        from app.services.stt import transcribe

        # 1 секунда тишины (PCM s16le 16k mono) — проверяем, что движок отвечает.
        silence = b"\x00\x00" * 16000
        await transcribe(silence, 1)
        print("  ✅ Движок распознавания ответил (на тишине текст пустой — это норма)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ STT упал: {type(exc).__name__}: {exc}")
        return False


async def check_gigachat() -> bool:
    print("— GigaChat (краткое содержание) —")
    if not settings.gigachat_basic_key:
        print("  ❌ Нет ключа: задай GIGACHAT_AUTH_KEY или пару CLIENT_ID+SECRET")
        return False
    try:
        await gigachat._token.get()  # noqa: SLF001
        print("  ✅ OAuth-токен получен")
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ OAuth не прошёл: {type(exc).__name__}: {exc}")
        return False
    try:
        answer = await gigachat.summarize("Привет! Это короткий тест связи с GigaChat.")
        print(f"  ✅ Ответ модели получен ({len(answer)} симв.)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ Запрос к модели упал: {type(exc).__name__}: {exc}")
        return False


async def main() -> None:
    print("=== Проверка бэкендов «Глашатай» ===\n")
    _print_env()
    stt_ok = await check_stt()
    print()
    giga_ok = await check_gigachat()
    print()
    print("Итог:")
    print(f"  STT ({settings.stt_backend}) : {'OK ✅' if stt_ok else 'FAIL ❌'}")
    print(f"  GigaChat            : {'OK ✅' if giga_ok else 'FAIL ❌'}")
    sys.exit(0 if (stt_ok and giga_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
