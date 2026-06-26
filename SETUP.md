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

## 3. Распознавание речи (STT)

По умолчанию `STT_BACKEND=whisper` — локальный **faster-whisper**, **ключи не нужны**,
ничего настраивать не надо. Модель зашита в образ (`WHISPER_MODEL`, по умолчанию
`base`; на 1 ГБ RAM поставь `tiny`). Можешь сразу переходить к шагу 4.

<details>
<summary>Опционально: облако SaluteSpeech (если когда-нибудь подключишь пакет)</summary>

Чтобы вместо Whisper использовать SaluteSpeech, задай `STT_BACKEND=salutespeech` и:

1. Зайди на [developers.sber.ru](https://developers.sber.ru) и войди через **Sber ID**.
2. Найди продукт **SaluteSpeech** (SmartSpeech) → **Создать проект / Получить API**.
3. Выбери тариф для **физлица** (есть бесплатный пакет минут в месяц), прими условия.
4. В проекте найди раздел с авторизацией. Там есть **три** значения:
   `Client ID`, `Client Secret` и **`Ключ авторизации` (Authorization key)**.
5. Заполни в `.env` **один из вариантов**:
   - **Вариант 1 (проще):** скопируй длинный **`Ключ авторизации`** (Base64,
     ~80–100 символов) в `SALUTE_SPEECH_AUTH_KEY`.
   - **Вариант 2:** впиши `Client ID` → `SALUTE_SPEECH_CLIENT_ID` и
     `Client Secret` → `SALUTE_SPEECH_CLIENT_SECRET` (ключ соберётся сам).
6. `SALUTE_SPEECH_SCOPE` оставь `SALUTE_SPEECH_PERS`.

> ⚠️ **Частая ошибка:** вставить в `*_AUTH_KEY` сам **Client ID** (это UUID на
> 36 символов вида `019f…-…-66c9`). Сервер ответит **401**. В `*_AUTH_KEY`
> нужен либо длинный Base64-ключ, либо используй вариант 2 (ID + Secret).

7. **Подключи пакет распознавания (иначе 402).** Получить ключ — мало: к проекту
   должен быть подключён пакет, **даже бесплатный**. Иначе вызов вернёт
   **402 Payment Required**, хотя OAuth проходит.
   - На странице **SaluteSpeech** (не GigaChat!) в блоке **Freemium** нажми
     **«Select service packages» / «Выбрать пакеты услуг»**. Это пакеты именно
     SaluteSpeech (минуты для распознавания / символы для синтеза) — они отдельные
     от биллинга GigaChat.
   - Выбери **бесплатный пакет минут для РАСПОЗНАВАНИЯ речи**, добавь в корзину и
     оформи (стоимость 0 ₽). Синтез нам не нужен.
   - Проверить остаток: SaluteSpeech → **«Статистика использования»**.

> ⚠️ Не путай с биллингом **GigaChat API** (там пакеты токенов). Пакеты
> SaluteSpeech подключаются только со страницы SaluteSpeech.

</details>

---

## 4. `GIGACHAT_AUTH_KEY` — краткое содержание (GigaChat)

1. Там же на [developers.sber.ru](https://developers.sber.ru) открой **GigaChat API**.
2. **Создать проект** для физлица, прими условия (бесплатный тариф для физлиц).
3. Заполни **один из вариантов** (как у SaluteSpeech):
   - **`Ключ авторизации`** (длинный Base64) → `GIGACHAT_AUTH_KEY`, **или**
   - `Client ID` → `GIGACHAT_CLIENT_ID` и `Client Secret` → `GIGACHAT_CLIENT_SECRET`.
4. `GIGACHAT_SCOPE` оставь `GIGACHAT_API_PERS`, модель `GIGACHAT_MODEL=GigaChat`.

> SaluteSpeech и GigaChat — это **разные** проекты и **разные** ключи, даже если
> кабинет один. Та же оговорка про Client ID vs Authorization key, что и выше.

---

## 🔎 Проверка ключей

После заполнения `.env` можно проверить связь с API (внутри Docker, где стоят
сертификаты Минцифры):

```bash
docker build -t glashatai:test .
docker run --rm --env-file .env glashatai:test python -m app.scripts.check_api
```

Скрипт покажет, проходят ли OAuth и реальные вызовы SaluteSpeech и GigaChat,
и подскажет, если в ключ случайно попал Client ID.

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
