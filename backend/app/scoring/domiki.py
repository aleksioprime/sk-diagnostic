"""Проективная методика «Домики» О. А. Ореховой (цветовой тест отношений).

Две версии: для начальных классов (domiki_emotion_primary) и для 7-х классов (domiki_emotion_middle),
отличаются набором домиков. Перенесено из скриптов NocoBase; формат результата прежний.
"""

import math
from dataclasses import dataclass

from app.scoring.common import ScoringError, now_iso, to_fixed

COLORS = {
    'blue': {'title': 'Синий', 'type': 'base_positive'},
    'green': {'title': 'Зеленый', 'type': 'base_positive'},
    'red': {'title': 'Красный', 'type': 'base_positive'},
    'yellow': {'title': 'Желтый', 'type': 'base_positive'},
    'violet': {'title': 'Фиолетовый', 'type': 'ambivalent'},
    'brown': {'title': 'Коричневый', 'type': 'negative'},
    'gray': {'title': 'Серый', 'type': 'neutral'},
    'black': {'title': 'Черный', 'type': 'negative'},
}

# Аутогенная норма 34251607: красный, жёлтый, зелёный, фиолетовый, синий, коричневый, серый, чёрный
AUTOGENIC_NORM = ['red', 'yellow', 'green', 'violet', 'blue', 'brown', 'gray', 'black']
BASE_POSITIVE_COLORS = ['blue', 'green', 'red', 'yellow']
NEGATIVE_COLORS = ['brown', 'black']
ATTENTION_COLORS = ['gray', 'brown', 'black']


@dataclass(frozen=True)
class Variant:
    houses: dict[str, str]  # код домика → название в результате
    school_codes: list[str]  # домики для «отношения к школе»
    # Подписи домиков в итоговой таблице; None — те же названия
    domain_titles: dict[str, str] | None = None
    custom_house: bool = False  # «Придумай сам» с описанием от ученика
    # Пояснение к пограничному эмоциональному фону: в версиях методики оно сформулировано по-разному
    borderline_text: str = (
        'Показатель находится между нормативным диапазоном и зоной преобладания отрицательных эмоций; '
        'требует дополнительной качественной интерпретации.'
    )


PRIMARY = Variant(
    houses={
        'soul': 'Твоя душа',
        'school_way': 'Когда ты идешь в школу',
        'reading_lesson': 'На уроке литературы',
        'writing_lesson': 'На уроке письма',
        'math_lesson': 'На уроке математики',
        'teacher_talk': 'Когда разговариваешь с учителем',
        'classmates': 'Когда общаешься с одноклассниками',
        'home': 'Когда находишься дома',
        'homework': 'Когда делаешь уроки',
        'custom_house': 'Собственный домик',
    },
    school_codes=[
        'school_way',
        'reading_lesson',
        'writing_lesson',
        'math_lesson',
        'teacher_talk',
        'classmates',
        'homework',
    ],
    domain_titles={
        'soul': 'Душа',
        'school_way': 'Идти в школу',
        'reading_lesson': 'Урок литературы',
        'writing_lesson': 'Урок письма',
        'math_lesson': 'Урок математики',
        'teacher_talk': 'Отношения с учителями',
        'classmates': 'Отношения с одноклассниками',
        'home': 'Отношение дома',
        'homework': 'Делать уроки',
        'custom_house': 'Придумай сам',
    },
    custom_house=True,
    borderline_text=(
        'Показатель находится между нормативным диапазоном и зоной преобладания отрицательных эмоций; '
        'по описанию методики требует дополнительной качественной интерпретации.'
    ),
)

MIDDLE = Variant(
    houses={
        'soul': 'Твоя душа',
        'school': 'Настроение в школе',
        'home': 'Настроение дома',
        'literature': 'Урок русского языка и литературы',
        'english': 'Урок английского языка',
        'mathematics': 'Урок математики',
        'history': 'Урок истории',
        'technology': 'Урок технологии',
        'physical_culture': 'Урок физкультуры',
        'biology': 'Урок биологии',
        'physics': 'Урок физики',
        'arts': 'Урок ИЗО',
        'test': 'Контрольные и проверочные работы',
        'board': 'Ответ у доски',
        'mentor': 'Общение с наставником',
        'classmates': 'Общение с одноклассниками',
        'homework': 'Выполнение домашних заданий',
    },
    school_codes=[
        'school',
        'literature',
        'english',
        'mathematics',
        'history',
        'technology',
        'physical_culture',
        'biology',
        'physics',
        'arts',
        'test',
        'board',
        'mentor',
        'classmates',
        'homework',
    ],
)


def _find(answers: list[dict], code: str) -> dict | None:
    return next((item for item in answers if item.get('question_code') == code), None)


def _color(answer: dict | None, code: str) -> str:
    if answer is None:
        raise ScoringError(f'Нет ответа на вопрос {code}')
    candidates = [
        answer.get('value'),
        (answer.get('scale_option') or {}).get('value'),
        (answer.get('selected_option') or {}).get('value'),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate in COLORS:
            return candidate
    raise ScoringError(f'Не удалось определить цвет для вопроса {code}')


def _text(answer: dict | None) -> str | None:
    if answer is None:
        return None
    for value in (answer.get('text'), answer.get('value')):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def preference_order(answer: dict | None) -> list[str]:
    if answer is None:
        raise ScoringError('Нет ответа на задание №1 (порядок цветов)')
    ranking = answer.get('ranking') or []
    if not ranking:
        raise ScoringError('В задании №1 цвета не расставлены')
    ordered = sorted(ranking, key=lambda item: item.get('rank') if item.get('rank') is not None else 999)
    colors = []
    for item in ordered:
        if item.get('option_value') not in COLORS:
            raise ScoringError(f'Некорректный цвет в задании №1: {item.get("option_value")}')
        colors.append(item['option_value'])
    if len(set(colors)) != 8:
        raise ScoringError('В задании №1 должно быть 8 разных цветов')
    return colors


def vegetative_coefficient(positions: dict[str, int]) -> float:
    denominator = 18 - positions['blue'] - positions['green']
    if denominator == 0:
        raise ScoringError('Невозможно вычислить вегетативный коэффициент: знаменатель равен нулю')
    return to_fixed((18 - positions['red'] - positions['blue']) / denominator)


def interpret_vegetative(vk: float) -> tuple[str, str, str]:
    if 0 <= vk <= 0.5:
        return (
            'critical_fatigue',
            'Хроническое переутомление',
            'Истощение, низкая работоспособность. Нагрузки непосильны для ребенка.',
        )
    if 0.51 <= vk <= 0.91:
        return (
            'compensated_fatigue',
            'Компенсируемое состояние усталости',
            'Самовосстановление оптимальной работоспособности происходит за счет периодического снижения '
            'активности. Необходима оптимизация рабочего ритма, режима труда и отдыха.',
        )
    if 0.92 <= vk < 2:
        return (
            'optimal',
            'Оптимальная работоспособность',
            'Ребенок отличается бодростью, здоровой активностью, готовностью к энергозатратам. Нагрузки '
            'соответствуют возможностям. Образ жизни позволяет ребенку восстанавливать затраченную энергию.',
        )
    return (
        'overexcitation',
        'Перевозбуждение',
        'Чаще является результатом работы ребенка на пределе своих возможностей, что приводит к быстрому '
        'истощению. Требуется нормализация темпа деятельности, режима труда и отдыха, а иногда и снижение '
        'нагрузки.',
    )


def total_deviation(order: list[str]) -> int:
    return sum(abs(order.index(color) - index) for index, color in enumerate(AUTOGENIC_NORM))


def interpret_deviation(value: int, borderline_text: str) -> tuple[str, str, str, str]:
    """Уровень, короткая подпись, название, интерпретация."""
    if value > 20:
        return (
            'negative_background',
            'отрицательный',
            'Преобладание отрицательных эмоций',
            'У ребенка доминируют плохое настроение и неприятные переживания. Имеются проблемы, которые '
            'ребенок не может решить самостоятельно.',
        )
    if 19 <= value <= 20:
        return (
            'borderline_background',
            'пограничный',
            'Пограничный эмоциональный фон',
            borderline_text,
        )
    if 10 <= value <= 18:
        return (
            'normal_background',
            'нормальный',
            'Эмоциональное состояние в норме',
            'Ребенок может радоваться и печалиться, поводов для беспокойства нет.',
        )
    return (
        'positive_background',
        'положительный',
        'Преобладание положительных эмоций',
        'Ребенок весел, счастлив, настроен оптимистично.',
    )


def self_esteem(order: list[str]) -> dict:
    first = order[0]
    if first in BASE_POSITIVE_COLORS:
        return {'value': 'positive', 'label': 'Положительная'}
    if first == 'violet':
        return {'value': 'infantile', 'label': 'Инфантильная'}
    if first in NEGATIVE_COLORS or first == 'gray':
        return {'value': 'negative', 'label': 'Отрицательная'}
    return {'value': 'unknown', 'label': 'Не определена'}


def relation(color: str) -> str:
    kind = COLORS[color]['type']
    if kind == 'base_positive':
        return 'positive'
    if kind == 'negative':
        return 'negative'
    return 'ambivalent'


RELATION_LABELS = {'positive': 'положительное', 'negative': 'негативное', 'ambivalent': 'амбивалентное'}


def summarize_relations(relations: list[str]) -> str:
    positive = relations.count('positive')
    negative = relations.count('negative')
    ambivalent = relations.count('ambivalent')
    half = math.ceil(len(relations) / 2)
    if len(relations) == 1:
        return relations[0]
    if negative > 0 and positive == 0 and ambivalent == 0:
        return 'negative'
    if positive > 0 and negative == 0 and ambivalent == 0:
        return 'positive'
    if negative >= half and positive == 0:
        return 'negative'
    if positive >= half and negative == 0 and ambivalent <= 1:
        return 'positive'
    return 'ambivalent'


SCHOOL_INTERPRETATION = {
    'positive': 'Эмоциональное отношение к школьной жизни выглядит положительным.',
    'negative': 'Есть признаки негативного эмоционального отношения к школьной жизни.',
    'ambivalent': 'Эмоциональное отношение к школьной жизни выглядит смешанным и требует дополнительного анализа.',
}


def calculate(data: dict, variant: Variant) -> dict:
    student = data.get('student')
    if not student:
        raise ScoringError('Отсутствуют данные ученика')
    answers = data.get('answers') or []
    if not answers:
        raise ScoringError('Отсутствуют ответы')

    order = preference_order(_find(answers, 'color_preference'))
    positions = {color: index + 1 for index, color in enumerate(order)}
    vk = vegetative_coefficient(positions)
    vk_level, vk_title, vk_text = interpret_vegetative(vk)
    deviation = total_deviation(order)
    dev_level, dev_label, dev_title, dev_text = interpret_deviation(deviation, variant.borderline_text)

    houses = {code: _color(_find(answers, code), code) for code in variant.houses}
    school = summarize_relations([relation(houses[code]) for code in variant.school_codes])

    titles = variant.domain_titles or variant.houses
    domains = []
    for code in titles:
        color = houses[code]
        attention = color in ATTENTION_COLORS
        item = {
            'code': code,
            'title': titles[code],
            'status': 'attention' if attention else 'ok',
            'status_label': 'Обратить внимание' if attention else 'Отклонений нет',
            'color_code': color,
            'color_title': COLORS[color]['title'],
        }
        if variant.custom_house and code == 'custom_house':
            item['description'] = _text(_find(answers, 'custom_house_description'))
        domains.append(item)

    return {
        'attempt': {'id': data.get('attempt_id'), 'submitted_at': data.get('submitted_at') or None},
        'test': {
            'id': data.get('test_id') or None,
            'code': data.get('test_code') or None,
            'title': data.get('test_title') or None,
        },
        'student': {
            key: student.get(key) or None for key in ('id', 'name', 'birth_date', 'age', 'gender', 'gender_value')
        },
        'result': {
            'calculated_at': now_iso(),
            'vegetative_coefficient': {
                'value': vk,
                'level': vk_level,
                'label': vk_title,
                'interpretation': vk_text,
            },
            'emotional_background': {
                'value': deviation,
                'level': dev_level,
                'label': dev_label,
                'title': dev_title,
                'interpretation': dev_text,
            },
            'self_esteem': self_esteem(order),
            'school_relation': {
                'value': school,
                'label': RELATION_LABELS[school],
                'interpretation': SCHOOL_INTERPRETATION[school],
            },
        },
        'domains': domains,
    }
