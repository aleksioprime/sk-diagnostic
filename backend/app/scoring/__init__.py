"""Расчёт результатов: скрипт на JavaScript, сохранённый в методике (tests.scoring_script)."""

import asyncio
from pathlib import Path

from app.scoring import sandbox
from app.scoring.common import ScoringError

# Исходные скрипты методик, перенесённых из NocoBase: ими заполнена база (миграция 0003) и загрузка из NocoBase
SCRIPTS_DIR = Path(__file__).parent / 'scripts'


def nocobase_script(test_code: str) -> str | None:
    path = SCRIPTS_DIR / f'{test_code}.js'
    return path.read_text(encoding='utf-8') if path.exists() else None


async def calculate(script: str | None, data: dict) -> dict:
    """Расчёт попытки. V8 работает вне цикла событий, чтобы долгий скрипт не задерживал остальные запросы."""
    if not script:
        raise ScoringError('У методики нет расчёта')
    return await asyncio.to_thread(sandbox.calculate, script, data)


__all__ = ['ScoringError', 'calculate', 'nocobase_script']
