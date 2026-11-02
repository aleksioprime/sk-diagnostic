"""Расчёт результатов методик. Методика выбирается по коду теста."""

from collections.abc import Callable

from app.scoring import domiki, motivation
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


__all__ = ['CALCULATORS', 'NEEDS_BIRTH_DATE', 'ScoringError', 'calculate']
