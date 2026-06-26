"""Entrypoint воркера arq.

Запускаем не через CLI `arq ...`, а напрямую: CLI arq ставит uvloop и на
Python 3.12 падает в `asyncio.get_event_loop()` (нет текущего цикла). Здесь
явно создаём event loop до старта воркера — надёжно и без uvloop.

Запуск:  python -m app.worker.run
"""

from __future__ import annotations

import asyncio

from arq.worker import run_worker

from app.worker.main import WorkerSettings


def main() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
