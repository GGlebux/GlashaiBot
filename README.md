<div align="center">

# Глашатай 📯

**Телеграм-бот, который превращает голосовые и кружки в текст и краткое содержание.**

Распознавание речи — [SaluteSpeech](https://developers.sber.ru/portal/products/smartspeech) ·
Краткое содержание — [GigaChat](https://developers.sber.ru/portal/products/gigachat) ·
Бесплатные облачные сервисы Сбера.

</div>

---

## Возможности

- 🎙 Расшифровка **голосовых сообщений** и **видео-кружков** в текст.
- 🧠 Краткое содержание расшифровки через GigaChat.
- 👀 Прогресс через эмодзи-реакции (принял → распознаю → готово).
- 🔗 Режим **цепочки**: `/begin` → несколько гс → `/end` → одно общее саммари.
- 🛡 Лимит сообщений в сутки на пользователя.
- 📊 Веб-админка со статистикой и управлением (вход через Telegram).
- 🐳 Полностью в Docker — поднимается одной командой.

> 🔒 **Приватность:** расшифровки и саммари нигде не сохраняются — только
> обезличенная статистика.

## Быстрый старт

> 📘 **Полная настройка с нуля** (как назвать бота + где взять каждый ключ для
> `.env`) — в **[SETUP.md](SETUP.md)**. Деплой на сервер — в **[DEPLOY.md](DEPLOY.md)**.

```bash
git clone <repo>
cd glashatai
cp .env.example .env       # заполни токены (см. SETUP.md)
docker compose up -d
```

Что нужно получить заранее (подробно — в [SETUP.md](SETUP.md)):

| Что | Где |
|---|---|
| 🤖 Токен бота | [@BotFather](https://t.me/BotFather) |
| 🔑 Ключ SaluteSpeech | [developers.sber.ru](https://developers.sber.ru) → SaluteSpeech |
| 🔑 Ключ GigaChat | [developers.sber.ru](https://developers.sber.ru) → GigaChat API |
| 🆔 Свой Telegram ID | [@userinfobot](https://t.me/userinfobot) |

**Имя бота:** display name `Глашатай 📯`, username вроде `@GlashataiBot`
(должен заканчиваться на `bot`). Детали и варианты — в [SETUP.md](SETUP.md).

## Разработка

```bash
docker compose -f docker-compose-dev.yml up --build
```

Собирает образ локально, монтирует исходники, перезапускается на изменениях.

## Архитектура

`bot` (aiogram) · `worker` (arq) · `admin` (FastAPI) · `postgres` · `redis`.
Подробнее — в [claude.md](claude.md).

## Лицензия

MIT
