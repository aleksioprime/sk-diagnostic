from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal


class ScoringError(Exception):
    """Ответы не позволяют посчитать результат: не хватает данных или они вне методики."""


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def gender_label(gender: str | None) -> str:
    return {'male': 'Мужской', 'female': 'Женский'}.get(gender or '', 'Не указан')


def to_fixed(value: float, digits: int = 2) -> float:
    """Округление как Number(x.toFixed(2)) в JavaScript: половина — вверх, по точному значению числа."""
    return float(Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))
