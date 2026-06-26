# 🚀 Настройка «Глашатай» с нуля

Пошагово: как назвать бота и где взять каждое значение для `.env`.
Идём сверху вниз — в конце просто заполняешь `.env` и запускаешь.

---

## 0. Имя бота (делаем самым первым)

При создании бота в Telegram у тебя спросят **два** имени — не путай их:

| Что | Правила Telegram | Рекомендация для нас |
|---|---|---|
| **Имя (display name)** | до 64 символов, любые буквы и эмодзи, можно менять в любой момент | **`Глашатай 📯`** |
| **Username** | 5–32 символа, только латиница/цифры/`_`, **обязан заканчиваться на `bot`**, уникален на весь Telegram | см. варианты ниже |

**Короткое имя (бренд):** `Глашатай`.

**Варианты username** (проверяй доступность прямо в @BotFather, занятые он отклонит):
- `@GlashataiBot` ← основной
- `@glashatai_bot`
- `@GlasVoiceBot`
- `@glashatai_voice_bot`
- `@GlasBot` (если свободен — самый короткий)

**Бонус для оформления** (зададим позже командами BotFather):
- Описание (`/setdescription`, до 512 симв.):
  > Превращаю голосовые и кружки в текст и краткое содержание. Пришли гс — пришлю расшифровку. 📯
- О боте (`/setabouttext`, до 120 симв.):
  > Голос → текст + саммари. Бесплатно, быстро, удобно.

---

## 1. `BOT_TOKEN` — токен бота

1. Открой [@BotFather](https://t.me/BotFather) → команда **/newbot**.
2. Введи **имя** (`Глашатай 📯`) и **username** (из вариантов выше).
3. BotFather пришлёт строку вида `123456789:AAE...` — это и есть `BOT_TOKEN`.

> Позже там же: `/setuserpic` (аватар), `/setdescription`, `/setabouttext`,
> `/setcommands` — для красивого оформления.

---

## 2. `ADMIN_IDS` — твой Telegram ID

1. Открой [@userinfobot](https://t.me/userinfobot) → он пришлёт твой числовой `Id`.
2. Впиши его в `ADMIN_IDS`. Несколько админов — через запятую: `11111111,22222222`.

---

## 3. `SALUTE_SPEECH_AUTH_KEY` — распознавание речи (SaluteSpeech)

1. Зайди на [developers.sber.ru](https://developers.sber.ru) и войди через **Sber ID**.
2. Найди продукт **SaluteSpeech** (SmartSpeech) → **Создать проект / Получить API**.
3. Выбери тариф для **физлица** (есть бесплатный пакет минут в месяц), прими условия.
4. В проекте найди раздел с авторизацией и скопируй **Authorization key**
   (длинная строка Base64 — это уже готовый ключ `client_id:client_secret`).
5. Вставь его в `SALUTE_SPEECH_AUTH_KEY`. `SALUTE_SPEECH_SCOPE` оставь `SALUTE_SPEECH_PERS`.

> Если в кабинете дают отдельно Client ID и Client Secret — закодируй
> `client_id:client_secret` в Base64 и используй результат как Authorization key.

---

## 4. `GIGACHAT_AUTH_KEY` — краткое содержание (GigaChat)

1. Там же на [developers.sber.ru](https://developers.sber.ru) открой **GigaChat API**.
2. **Создать проект** для физлица, прими условия (бесплатный тариф для физлиц).
3. Скопируй **Authorization key** проекта → в `GIGACHAT_AUTH_KEY`.
4. `GIGACHAT_SCOPE` оставь `GIGACHAT_API_PERS`, модель `GIGACHAT_MODEL=GigaChat`.

> SaluteSpeech и GigaChat — это **разные** ключи, даже если кабинет один.

---

## 5. Админка: `ADMIN_BASE_URL` и домен для входа

Вход в админку — через Telegram Login Widget, ему нужен **домен**.

1. Подними админку на домене (например, `https://admin.example.com`) — пропиши его в `ADMIN_BASE_URL`.
2. В [@BotFather](https://t.me/BotFather): **/setdomain** → выбери бота → укажи тот же домен.
3. `ADMIN_SECRET_KEY` — любая длинная случайная строка (сгенерируй, например,
   `python -c "import secrets; print(secrets.token_hex(32))"`).

> Для локальной проверки можно `ADMIN_BASE_URL=http://localhost:8080`, но виджет
> Telegram требует валидный домен — локально вход через Telegram не сработает.

---

## 6. Деплой: Docker Hub + GitHub Actions

1. Зарегистрируй репозиторий на Docker Hub, например `yourname/glashatai`.
2. Создай **Access Token**: Docker Hub → Account Settings → Security → New Access Token.
3. В GitHub-репозитории: Settings → Secrets and variables → Actions → добавь:
   - `DOCKERHUB_USERNAME` = твой логин Docker Hub
   - `DOCKERHUB_TOKEN` = созданный токен
4. В `.env` на сервере укажи `DOCKER_IMAGE=yourname/glashatai:latest`.

После пуша в `main` Actions соберёт образ и зальёт в Docker Hub, а **Watchtower**
на сервере подтянет свежий образ и перезапустит контейнеры.

---

## 7. Заполни `.env` и запусти

```bash
cp .env.example .env      # заполни значениями из шагов выше
docker compose up -d      # прод (образ из Docker Hub)
# или для разработки:
docker compose -f docker-compose-dev.yml up --build
```

Готово — пиши боту голосовое 🎙️
