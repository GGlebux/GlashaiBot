"""Вспомогательные функции бота."""

from __future__ import annotations

from aiogram import Bot

TG_LIMIT = 4096
CHUNK = 3900  # с запасом под разметку


async def send_html_chunks(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_to_message_id: int | None = None,
) -> None:
    """Отправляет длинный текст частями, не превышая лимит Telegram."""
    chunks = _split(text, CHUNK)
    for index, chunk in enumerate(chunks):
        await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode="HTML",
            reply_to_message_id=reply_to_message_id if index == 0 else None,
            disable_web_page_preview=True,
        )


def _split(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        # Очень длинная строка — режем жёстко.
        while len(line) > size:
            chunks.append(line[:size])
            line = line[size:]
        if len(current) + len(line) + 1 > size:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
