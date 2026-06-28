<div align="center">

# Глашатай 📯

**Телеграм-бот, который превращает голосовые и кружки в текст и краткое содержание.**

Распознавание речи — локальный [Whisper](https://github.com/SYSTRAN/faster-whisper) ·
Краткое содержание — [GigaChat](https://developers.sber.ru/portal/products/gigachat) (Сбер)

[Попробовать бота — @glashatai_voice_bot](https://t.me/glashatai_voice_bot)

</div>

---

## Возможности

- 🎙 Расшифровка **голосовых** и **видео-кружков** в текст.
- 🧠 Краткая **выжимка тезисами** (с эмодзи) + определение тона/стиля общения.
- 📊 Живой **прогресс-бар** обработки; полный текст — отдельным сообщением.
- 🔗 Режим **цепочки**: `/begin` → несколько гс → `/end` → одно общее саммари.
- 🛡 Лимит сообщений в сутки на пользователя.
- 🖥 Веб-админка со статистикой (вход через Telegram).
- 🐳 Полностью в Docker — поднимается одной командой.

> 🔒 **Приватность:** аудио, расшифровки и саммари нигде не сохраняются — только
> обезличенная статистика.

## Быстрый старт

```bash
git clone https://github.com/GGlebux/GlashaiBot.git
cd GlashaiBot
cp .env.example .env       # заполни значения (подсказки — в самом файле)
docker compose up -d
```

Что нужно получить заранее:

| Что | Где |
|---|---|
| 🤖 Токен бота | [@BotFather](https://t.me/BotFather) |
| 🔑 Ключ GigaChat | [developers.sber.ru](https://developers.sber.ru) → GigaChat API |
| 🆔 Свой Telegram ID | [@userinfobot](https://t.me/userinfobot) |

Распознавание по умолчанию локальное (Whisper, модель в образе) — ключи не нужны.
На VPS 2 ГБ хватает модели `small`/`base`. Все параметры — в `.env.example`.

## Разработка

```bash
docker compose -f docker-compose-dev.yml up --build
```

Собирает образ локально, монтирует исходники, перезапускается на изменениях.

## Архитектура

`bot` (aiogram) · `worker` (arq) · `admin` (FastAPI) · `postgres` · `redis` ·
`caddy` (авто-HTTPS). Деплой — GitHub Actions → Docker Hub → Watchtower.
Подробнее — в [claude.md](claude.md).

## Лицензия

MIT
