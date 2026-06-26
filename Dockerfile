FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Moscow

# Системные зависимости: ffmpeg (конвертация аудио), curl и сертификаты.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# Корневые сертификаты НУЦ Минцифры — нужны для TLS сервисов Сбера.
# Кладём в системный trust store и собираем отдельный bundle для httpx.
RUN set -eux; \
    curl -fsSL https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer \
        -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt; \
    curl -fsSL https://gu-st.ru/content/Other/doc/russian_trusted_sub_ca.cer \
        -o /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt; \
    update-ca-certificates; \
    { cat /usr/local/share/ca-certificates/russian_trusted_root_ca.crt; echo; \
      cat /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt; echo; } \
      > /etc/ssl/certs/russian_trusted_ca.pem

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Предзагрузка модели Whisper в образ — воркер не будет качать её при старте.
# Размер можно сменить при сборке: --build-arg WHISPER_MODEL=tiny
ARG WHISPER_MODEL=base
RUN python -c "from faster_whisper import download_model; download_model('${WHISPER_MODEL}')"

COPY app ./app

# По умолчанию запускается бот; worker и admin переопределяют command в compose.
CMD ["python", "-m", "app.bot.main"]
