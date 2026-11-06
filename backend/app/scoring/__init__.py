"""Расчёт результатов методик: встроенный (по коду теста) или скрипт, сохранённый в методике."""

import asyncio
from collections.abc import Callable

from app.scoring import domiki, motivation, sandbox
from app.scoring.common import ScoringError

CALCULATORS: dict[str, Callable[[dict], dict]] = {
    'motivation_learning': motivation.calculate,
    'domiki_emotion_primary': lambda data: domiki.calculate(data, domiki.PRIMARY),
    'domiki_emotion_middle': lambda data: domiki.calculate(data, domiki.MIDDLE),
}

# Методики, которым нужны возраст и пол ученика
NEEDS_BIRTH_DATE = {'motivation_learning'}


def calculate(test_code: str, data: dict) -> dict:
    calculator = CALCULATORS.get(test_code)
    if calculator is None:
        raise ScoringError(f'Для методики {test_code} нет расчёта')
    return calculator(data)


async def calculate_test(test_code: str, script: str | None, data: dict) -> dict:
    """Расчёт попытки. V8 работает вне цикла событий, чтобы долгий скрипт не задерживал остальные запросы."""
    if script:
        return await asyncio.to_thread(sandbox.calculate, script, data)
    return calculate(test_code, data)


__all__ = ['CALCULATORS', 'NEEDS_BIRTH_DATE', 'ScoringError', 'calculate', 'calculate_test']
