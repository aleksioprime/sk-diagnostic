"""Расчёты методик совпадают с результатами NocoBase. Выборка обезличена: без имён, ID и дат рождения."""

import json
from pathlib import Path

import pytest

from app.scoring import ScoringError, builtin_script, calculate, domiki
from app.scoring.sandbox import run_script

FIXTURES = Path(__file__).parent / 'fixtures'
CASES = json.loads((FIXTURES / 'nocobase_results.json').read_text())
# Примеры из старого репозитория, прогнанные через скрипты NocoBase (в том числе «Домики» начальной школы,
# по которым в NocoBase ещё не было результатов)
EXAMPLES = json.loads((FIXTURES / 'js_examples.json').read_text())


def _strip(result: dict) -> dict:
    result = json.loads(json.dumps(result))
    result['result'].pop('calculated_at', None)
    return result


@pytest.mark.parametrize('case', CASES, ids=lambda c: f'{c["input"]["test_code"]}-{c["input"]["attempt_id"]}')
def test_same_as_nocobase(case):
    assert _strip(calculate(case['input']['test_code'], case['input'])) == case['output']


@pytest.mark.parametrize('case', EXAMPLES, ids=lambda c: f'{c["input"]["test_code"]}-{c["input"]["attempt_id"]}')
def test_same_as_nocobase_scripts(case):
    if 'error' in case['output']:
        with pytest.raises(ScoringError):
            calculate(case['input']['test_code'], case['input'])
    else:
        assert _strip(calculate(case['input']['test_code'], case['input'])) == case['output']


def test_motivation_needs_age():
    case = next(c for c in CASES if c['input']['test_code'] == 'motivation_learning')
    data = {**case['input'], 'student': {**case['input']['student'], 'age': None}}
    with pytest.raises(ScoringError, match='возраст'):
        calculate('motivation_learning', data)


def test_primary_domiki_with_custom_house():
    colors = ['blue', 'green', 'red', 'yellow', 'violet', 'brown', 'gray', 'black']
    answers = [
        {
            'question_code': 'color_preference',
            'ranking': [{'option_value': c, 'rank': i} for i, c in enumerate(colors, 1)],
        },
        {'question_code': 'custom_house_description', 'text': ' Домик для кота '},
    ]
    answers += [
        {'question_code': code, 'value': 'black' if code == 'math_lesson' else 'green'}
        for code in domiki.PRIMARY.houses
    ]
    result = calculate('domiki_emotion_primary', {'student': {'id': 1}, 'answers': answers})

    assert result['result']['vegetative_coefficient']['value'] == 0.93  # (18 − 3 − 1) / (18 − 1 − 2)
    assert result['result']['self_esteem']['value'] == 'positive'
    math = next(d for d in result['domains'] if d['code'] == 'math_lesson')
    assert math['status'] == 'attention' and math['title'] == 'Урок математики'
    custom = next(d for d in result['domains'] if d['code'] == 'custom_house')
    assert custom['description'] == 'Домик для кота'


def test_to_fixed_rounds_half_up_like_javascript():
    from app.scoring.common import to_fixed

    assert to_fixed(0.125) == 0.13
    assert to_fixed(14 / 15) == 0.93


@pytest.mark.parametrize('case', EXAMPLES, ids=lambda c: f'{c["input"]["test_code"]}-{c["input"]["attempt_id"]}')
def test_js_script_of_builtin_matches_python(case):
    """Копия встроенной методики получает JS-скрипт: он обязан считать так же, как встроенный расчёт."""
    code = case['input']['test_code']
    run = run_script(builtin_script(code), case['input'])
    assert run.error is None
    expected = calculate(code, case['input'])
    for data in (run.output, expected):
        (data.get('result') or {}).pop('calculated_at', None)
        data.pop('calculated_at', None)
    assert run.output == expected
