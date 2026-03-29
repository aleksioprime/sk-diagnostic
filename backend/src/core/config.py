from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    project_name: str = Field(alias='PROJECT_NAME', default='SK Diagnostic API')
    project_description: str = Field(
        alias='PROJECT_DESCRIPTION',
        default='FastAPI BFF for anonymous diagnostic attempts',
    )

    default_host: str = Field(alias='HOST', default='0.0.0.0')
    default_port: int = Field(alias='PORT', default=8000)
    api_prefix: str = '/api/v1'

    nocobase_url: str = Field(alias='NOCOBASE_URL', default='')
    vite_api_url: str = Field(alias='VITE_API_URL', default='https://flow.skeducator.ru')
    api_key: str = Field(alias='API_KEY', default='')
    nocobase_timeout: float = Field(alias='NOCOBASE_TIMEOUT', default=30.0)

    cors_allow_origins_str: str = Field(
        alias='CORS_ALLOW_ORIGINS',
        default='http://localhost:3000,http://127.0.0.1:3000',
    )
    timezone: str = Field(alias='TIMEZONE', default='Europe/Moscow')

    @property
    def cors_allow_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allow_origins_str.split(',') if origin.strip()]

    @property
    def nocobase_api_url(self) -> str:
        base = (self.nocobase_url or self.vite_api_url or 'https://flow.skeducator.ru').rstrip('/')
        return base if base.endswith('/api') else f'{base}/api'


settings = Settings()
