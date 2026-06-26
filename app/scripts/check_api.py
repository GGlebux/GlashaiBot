"""Диагностика доступности API Сбера (SaluteSpeech + GigaChat).

Запуск (лучше в контейнере, где стоят сертификаты Минцифры):
    docker run --rm --env-file .env <image> python -m app.scripts.check_api

Секреты не печатаются (только маска). Проверяем: TLS + OAuth + реальный вызов.
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.config import settings
from app.services import gigachat, salute_speech


def _mask(value: str) -> str:
    if not value:
        return "(пусто)"
    if len(value) <= 10:
        return f"(len={len(value)})"
    return f"{value[:4]}…{value[-4:]} (len={len(value)})"


def _looks_like_uuid(value: str) -> bool:
    parts = value.split("-")
    return len(value) == 36 and len(parts) == 5


def _warn_uuid(name: str, auth_key: str) -> None:
    if auth_key and _looks_like_uuid(auth_key):
        print(
            f"  ⚠️  {name}_AUTH_KEY похож на Client ID (UUID, 36 симв.), а нужен\n"
            f"      «Ключ авторизации» (длинная Base64-строка). Либо задай пару\n"
            f"      {name}_CLIENT_ID + {name}_CLIENT_SECRET — соберём ключ сами."
        )


def _print_env() -> None:
    bundle = settings.sber_ca_bundle
    exists = os.path.exists(bundle) if bundle else False
    print("Окружение:")
    print(f"  verify_ssl          : {settings.sber_verify_ssl}")
    print(f"  ca_bundle           : {bundle} (существует: {exists})")
    print(f"  SaluteSpeech key    : {_mask(settings.salute_basic_key)}  scope={settings.salute_speech_scope}")
    print(f"  GigaChat key        : {_mask(settings.gigachat_basic_key)}  scope={settings.gigachat_scope}  model={settings.gigachat_model}")
    if not exists:
        print("  ⚠️  bundle сертификатов не найден — вне Docker TLS к Сберу, скорее всего, упадёт.")
    _warn_uuid("SALUTE_SPEECH", settings.salute_speech_auth_key)
    _warn_uuid("GIGACHAT", settings.gigachat_auth_key)
    print()


async def check_salute() -> bool:
    print("— SaluteSpeech (распознавание) —")
    if not settings.salute_basic_key:
        print("  ❌ Нет ключа: задай SALUTE_SPEECH_AUTH_KEY или пару CLIENT_ID+SECRET")
        return False
    try:
        await salute_speech._token.get()  # noqa: SLF001
        print("  ✅ OAuth-токен получен")
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ OAuth не прошёл: {type(exc).__name__}: {exc}")
        return False
    try:
        # 1 секунда тишины (PCM s16le 16k mono) — проверяем сам эндпоинт распознавания.
        silence = b"\x00\x00" * salute_speech.PCM_SAMPLE_RATE
        await salute_speech._recognize_sync(silence, "ru-RU")  # noqa: SLF001
        print("  ✅ speech:recognize ответил (на тишине текст пустой — это нормально)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ speech:recognize упал: {type(exc).__name__}: {exc}")
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
    print("=== Проверка API Сбера для «Глашатай» ===\n")
    _print_env()
    salute_ok = await check_salute()
    print()
    giga_ok = await check_gigachat()
    print()
    print("Итог:")
    print(f"  SaluteSpeech : {'OK ✅' if salute_ok else 'FAIL ❌'}")
    print(f"  GigaChat     : {'OK ✅' if giga_ok else 'FAIL ❌'}")
    sys.exit(0 if (salute_ok and giga_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
