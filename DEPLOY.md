# 🚀 Деплой «Глашатай» на сервер

Схема: **push в `main` → GitHub Actions собирает образ → Docker Hub → Watchtower
на сервере подтягивает свежий образ и перезапускает контейнеры.**

То есть после первой настройки деплой = просто `git push`.

---

## Часть 1. Настройка CI (один раз)

1. Заведи репозиторий на **Docker Hub**, например `youruser/glashatai`.
2. Docker Hub → Account Settings → Security → **New Access Token** (скопируй).
3. В GitHub-репозитории: Settings → Secrets and variables → **Actions** → New secret:
   - `DOCKERHUB_USERNAME` = твой логин Docker Hub
   - `DOCKERHUB_TOKEN` = токен из п.2
4. Сделай `git push` в `main` — вкладка **Actions** покажет сборку. По завершении
   в Docker Hub появится образ `youruser/glashatai:latest`.

> Образ содержит модель Whisper `small` (~0.5 ГБ) — сборка идёт пару минут, это норма.

---

## Часть 2. Сервер (один раз)

Нужен VPS (рекомендую **2 ГБ RAM**, Ubuntu 22.04+, ≥15 ГБ диска).

1. **Установи Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
2. **Положи на сервер `docker-compose.yml` и `.env`.** Проще склонировать репозиторий:
   ```bash
   git clone https://github.com/GGlebux/GlashaiBot.git
   cd GlashaiBot
   cp .env.example .env
   ```
3. **Заполни `.env`** (см. [SETUP.md](SETUP.md)) и обязательно укажи:
   ```
   DOCKER_IMAGE=youruser/glashatai:latest
   WHISPER_MODEL=small
   GIGACHAT_MODEL=GigaChat-Max
   ```
4. **Запусти:**
   ```bash
   docker compose up -d
   ```
5. **Проверь логи:**
   ```bash
   docker compose logs -f bot worker
   ```
   Бот должен написать «Глашатай запущен 📯», воркер — «Модель Whisper готова».

Готово — бот в проде. 🎉

---

## Часть 3. Обновления (постоянно)

Просто пушишь в `main`:
```
git push        →  Actions собирает образ  →  Docker Hub  →  Watchtower (раз в 5 мин)
                                                              сам обновляет контейнеры
```
Заходить на сервер не нужно.

---

## Проверка ключей на сервере (по желанию)
```bash
docker run --rm --env-file .env youruser/glashatai:latest python -m app.scripts.check_api
```

## Админка с HTTPS (вход через Telegram)

Вход в админку — через Telegram Login Widget, ему нужен **домен + HTTPS** (IP и
`http` не подходят). В стек уже встроен **Caddy** — он сам выпустит сертификат
Let's Encrypt. Нужен только бесплатный домен.

1. **Домен (бесплатно, быстро):** на [duckdns.org](https://www.duckdns.org) войди
   через Google, создай поддомен (напр. `glashatai`), в поле IP впиши адрес VPS →
   получишь `glashatai.duckdns.org`.
2. **Открой порты на сервере:** 80 и 443 (для Let's Encrypt и HTTPS).
   ```bash
   ufw allow 80 && ufw allow 443
   ```
3. **В `.env`:**
   ```
   DOMAIN=glashatai.duckdns.org
   ADMIN_BASE_URL=https://glashatai.duckdns.org
   ```
4. **В @BotFather:** `/setdomain` → выбери бота → впиши `glashatai.duckdns.org`.
5. `docker compose up -d` — Caddy поднимет HTTPS автоматически (первый запрос к
   домену может занять несколько секунд на выпуск сертификата).

Открой `https://glashatai.duckdns.org` → войди через Telegram (доступ только у
`ADMIN_IDS`).

> Без домена бот полностью работает — недоступен только веб-вход в админку.
> Caddy на работу бота не влияет: даже если сертификат не выпустится, бот живёт.

## Памятка по ресурсам (2 ГБ)
- `WHISPER_MODEL=small` — комфортно. `medium` на 2 ГБ не влезет.
- Желательно добавить **swap 2 ГБ** как страховку:
  ```bash
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  ```
- Воркер обрабатывает по одному сообщению за раз (`max_jobs=1`) — это специально,
  чтобы не упереться в память.
