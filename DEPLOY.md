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

## Админка (опционально)
Веб-дашборд работает, но вход через Telegram требует **домена** (для Login Widget):
- направь домен на сервер, открой порт `ADMIN_PORT` (8080) через reverse-proxy
  (nginx/Caddy) с HTTPS, укажи `ADMIN_BASE_URL=https://твой-домен`,
- в @BotFather → `/setdomain` пропиши этот домен.

Без домена бот полностью работает — недоступен только веб-вход в админку.

## Памятка по ресурсам (2 ГБ)
- `WHISPER_MODEL=small` — комфортно. `medium` на 2 ГБ не влезет.
- Желательно добавить **swap 2 ГБ** как страховку:
  ```bash
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  ```
- Воркер обрабатывает по одному сообщению за раз (`max_jobs=1`) — это специально,
  чтобы не упереться в память.
