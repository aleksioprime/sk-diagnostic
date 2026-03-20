from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Report Service'
    report_api_token: str = 'change-me'
    report_base_url: str = 'http://localhost:8000'
    report_storage_dir: str = '/app/output'
    report_templates_dir: str = '/app/templates'
    gotenberg_url: str = 'http://gotenberg:3000'
    enable_pdf: bool = True
    enable_xlsx: bool = True
    cleanup_after_hours: int = 24


settings = Settings()
