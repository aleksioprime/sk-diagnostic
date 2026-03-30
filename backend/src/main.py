"""
Точка входа FastAPI-приложения.

Создаёт экземпляр приложения, подключает CORS-мидлварь,
мидлварь логирования запросов и маршруты API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.core.config import settings
from src.core.logging import RequestLoggingMiddleware, get_logger
from src.routes.v1 import router

logger = get_logger(__name__)

app = FastAPI(
    version="0.1.0",
    title=settings.project_name,
    description=settings.project_description,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
)

# ─── Middleware (порядок важен: первый добавленный — последний выполняемый) ───

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    """Простой эндпоинт для проверки работоспособности сервиса."""
    return {"status": "ok"}


app.include_router(router, prefix=settings.api_prefix)

logger.info(
    "Приложение '%s' инициализировано, prefix=%s",
    settings.project_name,
    settings.api_prefix,
)
