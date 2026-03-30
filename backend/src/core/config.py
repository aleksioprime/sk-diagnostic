"""
Настройки приложения, загружаемые из переменных окружения / .env-файла.

Использует ``pydantic-settings`` для валидации и парсинга.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения, собираемая из env-переменных."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    # ─── Метаданные проекта ───────────────────────────────────────────────
    project_name: str = Field(alias='PROJECT_NAME', default='SK Diagnostic API')
    project_description: str = Field(
        alias='PROJECT_DESCRIPTION',
        default='FastAPI BFF for anonymous diagnostic attempts',
    )

    # ─── Сеть ─────────────────────────────────────────────────────────────
    default_host: str = Field(alias='HOST', default='0.0.0.0')
    default_port: int = Field(alias='PORT', default=8000)
    api_prefix: str = '/api/v1'

    # ─── NocoBase ─────────────────────────────────────────────────────────
    nocobase_url: str = Field(alias='NOCOBASE_URL', default='')
    vite_api_url: str = Field(alias='VITE_API_URL', default='https://flow.skeducator.ru')
    api_key: str = Field(alias='API_KEY', default='')
    nocobase_timeout: float = Field(alias='NOCOBASE_TIMEOUT', default=30.0)

    # ─── CORS ─────────────────────────────────────────────────────────────
    cors_allow_origins_str: str = Field(
        alias='CORS_ALLOW_ORIGINS',
        default='http://localhost:3000,http://127.0.0.1:3000',
    )

    # ─── Прочее ───────────────────────────────────────────────────────────
    timezone: str = Field(alias='TIMEZONE', default='Europe/Moscow')

    @property
    def cors_allow_origins(self) -> list[str]:
        """Список разрешённых Origin для CORS."""
        return [origin.strip() for origin in self.cors_allow_origins_str.split(',') if origin.strip()]

    @property
    def nocobase_api_url(self) -> str:
        """Базовый URL до ``/api`` эндпоинта NocoBase."""
        base = (self.nocobase_url or self.vite_api_url or 'https://flow.skeducator.ru').rstrip('/')
        return base if base.endswith('/api') else f'{base}/api'


settings = Settings()
