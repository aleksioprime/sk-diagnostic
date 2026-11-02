"""Фоновые задачи на arq: письма со ссылкой входа и синхронизация справочника SkolStream."""

import logging

from sk_common import worker
from sk_common.web import setup_logging

from app.core.config import settings

logger = logging.getLogger('sk_diagnostic.worker')


async def startup(ctx: dict) -> None:
    setup_logging()
    logger.info('Воркер запущен, окружение %s', settings.environment)


class WorkerSettings:
    functions = worker.FUNCTIONS
    cron_jobs = worker.CRON_JOBS
    on_startup = startup
    max_tries = 3
    redis_settings = worker.redis_settings()
