import sk_common
from sk_common.config import AuthSettings, DatabaseSettings, ServiceSettings, SmtpSettings


class DiagnosticDatabaseSettings(DatabaseSettings):
    user: str = 'sk_diagnostic'
    password: str = 'sk_diagnostic'
    name: str = 'sk_diagnostic'


class DiagnosticSmtpSettings(SmtpSettings):
    sender: str = 'SK Diagnostic <skolstream@yandex.ru>'


class DiagnosticAuthSettings(AuthSettings):
    access_cookie: str = 'skd_access'
    refresh_cookie: str = 'skd_refresh'


class Settings(ServiceSettings):
    """Общие поля (БД, Redis, почта, SkolStream, вход) — в sk_common.config.ServiceSettings."""

    project_name: str = 'SK Diagnostic'
    brand_color: str = '#4338ca'
    app_url: str = 'http://localhost:8701'
    cors_origins: list[str] = ['http://localhost:8701']
    # Перенос из NocoBase (python -m app.cli nocobase-fetch)
    nocobase_url: str = ''
    nocobase_api_key: str = ''

    db: DiagnosticDatabaseSettings = DiagnosticDatabaseSettings()
    smtp: DiagnosticSmtpSettings = DiagnosticSmtpSettings()
    auth: DiagnosticAuthSettings = DiagnosticAuthSettings()


settings = Settings()
sk_common.configure(settings)
