"""
Модуль настройки логирования для приложения.

Предоставляет:
- get_logger — фабрику именованных логгеров;
- RequestLoggingMiddleware — ASGI-мидлварь для записи входящих HTTP-запросов и ответов.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ─── Формат и уровень ────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s │ %(levelname)-7s │ %(name)-26s │ %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    stream=sys.stdout,
)

# Уменьшаем шум от httpx и uvicorn
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Вернуть логгер с указанным именем."""
    return logging.getLogger(name)


# ─── Middleware ───────────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Логирует каждый входящий HTTP-запрос и время его обработки.

    Пример строки в логе::

        → GET /api/v1/public/attempts/abc123  ← 200 (42 ms)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger = get_logger("http")
        method = request.method
        path = request.url.path
        query = str(request.url.query)
        full_path = f"{path}?{query}" if query else path

        logger.info("→ %s %s", method, full_path)
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        logger.info("← %s %s  %d (%d ms)", method, full_path, response.status_code, elapsed_ms)

        return response
