"""Методика диагностики мотивации учения и эмоционального отношения к учению (10–16 лет).

Перенесено из скрипта NocoBase «Расчёт диагностики мотивации»; формат результата прежний.
"""

from app.scoring.common import ScoringError, gender_label, now_iso

# Номера вопросов по шкалам
SCALES = {
    'cognitive_activity': [2, 6, 10, 14, 18, 22, 26, 30, 34, 38],  # Познавательная активность
    'achievement_motivation': [4, 8, 12, 16, 20, 24, 28, 32, 36, 40],  # Мотивация достижения
    'anxiety': [1, 5, 9, 13, 17, 21, 25, 29, 33, 37],  # Тревожность
    'anger': [3, 7, 11, 15, 19, 23, 27, 31, 35, 39],  # Гнев
}

# Обратные пункты (motivation_v2.docx): веса 1→4, 2→3, 3→2, 4→1
REVERSED = {
    'cognitive_activity': [14, 30, 38],
    'achievement_motivation': [4, 20, 32],
    'anxiety': [1, 9, 25, 33],
    'anger': [],
}

SCALE_TITLES = {
    'cognitive_activity': 'Познавательная активность',
    'achievement_motivation': 'Мотивация достижения',
    'anxiety': 'Тревожность',
    'anger': 'Гнев',
}


def _norm(ca, am, an, ag):
    return {'cognitive_activity': ca, 'achievement_motivation': am, 'anxiety': an, 'anger': ag}


# Нормы: возрастная группа → пол → шкала → уровень → [от, до]
NORMS = {
    '10-11': {
        'female': _norm(
            {'high': (31, 40), 'medium': (21, 26), 'low': (10, 25)},
            {'high': (32, 40), 'medium': (22, 31), 'low': (10, 21)},
            {'high': (27, 40), 'medium': (20, 26), 'low': (10, 19)},
            {'high': (21, 40), 'medium': (14, 20), 'low': (10, 13)},
        ),
        'male': _norm(
            {'high': (28, 40), 'medium': (22, 27), 'low': (10, 21)},
            {'high': (29, 40), 'medium': (21, 28), 'low': (10, 20)},
            {'high': (24, 40), 'medium': (17, 23), 'low': (10, 16)},
            {'high': (20, 40), 'medium': (13, 19), 'low': (10, 12)},
        ),
    },
    '12-14': {
        'female': _norm(
            {'high': (28, 40), 'medium': (21, 27), 'low': (10, 20)},
            {'high': (31, 40), 'medium': (23, 30), 'low': (10, 22)},
            {'high': (25, 40), 'medium': (19, 24), 'low': (10, 18)},
            {'high': (19, 40), 'medium': (14, 19), 'low': (10, 13)},
        ),
        'male': _norm(
            {'high': (27, 40), 'medium': (19, 26), 'low': (10, 18)},
            {'high': (25, 40), 'medium': (18, 24), 'low': (10, 17)},
            {'high': (26, 40), 'medium': (19, 25), 'low': (10, 18)},
            {'high': (23, 40), 'medium': (15, 22), 'low': (10, 14)},
        ),
    },
    '15-16': {
        'female': _norm(
            {'high': (29, 40), 'medium': (18, 28), 'low': (10, 17)},
            {'high': (31, 40), 'medium': (22, 30), 'low': (10, 21)},
            {'high': (25, 40), 'medium': (17, 24), 'low': (10, 16)},
            {'high': (21, 40), 'medium': (14, 20), 'low': (10, 13)},
        ),
        'male': _norm(
            {'high': (31, 40), 'medium': (21, 29), 'low': (10, 20)},
            {'high': (26, 40), 'medium': (18, 25), 'low': (10, 17)},
            {'high': (23, 40), 'medium': (16, 22), 'low': (10, 15)},
            {'high': (18, 40), 'medium': (12, 18), 'low': (10, 11)},
        ),
    },
}

LEVELS = [
    (
        45,
        60,
        'I',
        'Продуктивная мотивация с выраженным преобладанием познавательной мотивации учения '
        'и положительным эмоциональным отношением к нему',
    ),
    (29, 44, 'II', 'Продуктивная мотивация, позитивное отношение к учению, соответствие социальному нормативу'),
    (13, 28, 'III', 'Средний уровень с несколько сниженной познавательной мотивацией'),
    (
        -2,
        12,
        'IV',
        'Сниженная мотивация, переживание «школьной скуки», отрицательное эмоциональное отношение к учению',
    ),
]

# Качественная интерпретация (таблица «Интерпретация данных»): ПА, тревожность, гнев
INTERPRETATION_RULES = [
    (['high'], ['low', 'medium'], ['low'], 'Продуктивная мотивация и позитивное эмоциональное отношение к учению'),
    (['medium'], ['low', 'medium'], ['low'], 'Позитивное отношение к учению'),
    (['low'], ['low', 'medium'], ['low', 'medium'], 'Переживание «школьной скуки»'),
    (['medium'], ['low', 'medium'], ['low', 'medium'], 'Диффузное эмоциональное отношение'),
    (
        ['medium'],
        ['low', 'medium'],
        ['high'],
        'Диффузное эмоциональное отношение при фрустрированности значимых потребностей',
    ),
    (['low'], ['low'], ['high'], 'Резко отрицательное отношение к школе и учению'),
    (['low'], ['low', 'medium'], ['high'], 'Негативное эмоциональное отношение'),
    (
        ['high'],
        ['high'],
        ['high'],
        'Чрезмерно повышенная эмоциональность на уроке, обусловленная неудовлетворением ведущих '
        'социогенных потребностей',
    ),
    (['high'], ['high'], ['medium'], 'Повышенная эмоциональность на уроке'),
    (['medium', 'low'], ['high'], ['medium', 'low'], 'Школьная тревожность'),
    (['high'], ['medium', 'low'], ['high'], 'Позитивное отношение при фрустрированности потребностей'),
    (
        ['high', 'medium'],
        ['high'],
        ['low', 'medium'],
        'Позитивное отношение при повышенной чувствительности к оценочному аспекту.',
    ),
]

LEVEL_LABELS = {'high': 'высокий', 'medium': 'средний', 'low': 'низкий'}


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def answers_map(answers: list[dict]) -> dict[int, float]:
    result = {}
    for item in answers:
        number = item.get('question_number')
        if number is None:
            continue
        value = _number(item.get('value'))
        if value is None and item.get('selected_option'):
            value = _number(item['selected_option'].get('value'))
        if value is not None:
            result[int(number)] = value
    return result


def _answer(number: int, scale: str, values: dict[int, float]) -> int:
    raw = values.get(number)
    if raw not in (1, 2, 3, 4):
        raise ScoringError(f'Некорректный или отсутствующий ответ для вопроса {number}')
    raw = int(raw)
    return 5 - raw if number in REVERSED[scale] else raw


def _scale_sum(scale: str, values: dict[int, float]) -> int:
    return sum(_answer(number, scale, values) for number in SCALES[scale])


def level_description(total: int) -> tuple[str, str]:
    for low, high, level, text in LEVELS:
        if low <= total <= high:
            return level, text
    return 'V', 'Резко отрицательное отношение к учению'


def age_group(age: int) -> str:
    if age < 0:
        raise ScoringError('Возраст не может быть отрицательным')
    if age <= 11:
        return '10-11'
    if age <= 14:
        return '12-14'
    return '15-16'


def _level_by_norm(value: int, norm: dict) -> str:
    for level in ('high', 'medium', 'low'):
        low, high = norm[level]
        if low <= value <= high:
            return level
    raise ScoringError(f'Значение {value} вне диапазонов')


def norm_levels(scales: dict[str, int], age: int, gender: str) -> dict[str, str]:
    norms = NORMS[age_group(age)].get(gender)
    if norms is None:
        raise ScoringError(f'Не найдены нормы для пола "{gender}" и возрастной группы {age_group(age)}')
    return {code: _level_by_norm(scales[code], norms[code]) for code in SCALES}


def interpretation(levels: dict[str, str]) -> str:
    for pa, anxiety, anger, text in INTERPRETATION_RULES:
        if levels['cognitive_activity'] in pa and levels['anxiety'] in anxiety and levels['anger'] in anger:
            return text
    return 'Качественная интерпретация для данного сочетания шкал не определена.'


def calculate(data: dict) -> dict:
    student = data.get('student')
    if not student:
        raise ScoringError('Отсутствуют данные ученика')
    if student.get('age') is None:
        raise ScoringError('Не указан возраст ученика (дата рождения)')
    if not student.get('gender'):
        raise ScoringError('Не указан пол ученика')

    values = answers_map(data.get('answers') or [])
    scales = {code: _scale_sum(code, values) for code in SCALES}
    total = scales['cognitive_activity'] + scales['achievement_motivation'] - scales['anxiety'] - scales['anger']
    level, description = level_description(total)
    levels = norm_levels(scales, student['age'], student['gender'])

    return {
        'attempt': {'id': data.get('attempt_id'), 'submitted_at': data.get('submitted_at')},
        'test': {'code': data.get('test_code'), 'title': data.get('test_title') or None},
        'student': {
            'id': student.get('id'),
            'name': student.get('name') or None,
            'birth_date': student.get('birth_date') or None,
            'age': student['age'],
            'gender': student['gender'],
            'gender_value': student.get('gender_value') or None,
            'gender_label': gender_label(student['gender']),
        },
        'result': {
            'level': level,
            'total_score': total,
            'level_description': description,
            'interpretation': interpretation(levels),
            'calculated_at': now_iso(),
        },
        'scales': [
            {
                'code': code,
                'title': SCALE_TITLES[code],
                'value': scales[code],
                'level': levels[code],
                'level_label': LEVEL_LABELS[levels[code]],
            }
            for code in SCALES
        ],
    }
