"""Скрипты методик совпадают с результатами NocoBase. Выборка обезличена: без имён, ID и дат рождения."""

import json
from pathlib import Path

import pytest

from app.scoring import nocobase_script
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


def _run(data: dict):
    return run_script(nocobase_script(data['test_code']), data)


@pytest.mark.parametrize('case', CASES, ids=lambda c: f'{c["input"]["test_code"]}-{c["input"]["attempt_id"]}')
def test_same_as_nocobase(case):
    run = _run(case['input'])
    assert run.error is None
    assert _strip(run.output) == case['output']


@pytest.mark.parametrize('case', EXAMPLES, ids=lambda c: f'{c["input"]["test_code"]}-{c["input"]["attempt_id"]}')
def test_same_as_nocobase_scripts(case):
    run = _run(case['input'])
    if 'error' in case['output']:
        assert run.error
    else:
        assert run.error is None
        assert _strip(run.output) == case['output']


def test_motivation_needs_age():
    case = next(c for c in CASES if c['input']['test_code'] == 'motivation_learning')
    data = {**case['input'], 'student': {**case['input']['student'], 'age': None}}
    assert 'возраст' in _run(data).error.lower()


def test_primary_domiki_with_custom_house():
    example = next(c['input'] for c in EXAMPLES if c['input']['test_code'] == 'domiki_emotion_primary')
    colors = ['blue', 'green', 'red', 'yellow', 'violet', 'brown', 'gray', 'black']
    answers = []
    for answer in example['answers']:
        code = answer['question_code']
        if code == 'color_preference':
            ranking = [{'option_value': c, 'rank': i} for i, c in enumerate(colors, 1)]
            answers.append({**answer, 'ranking': ranking})
        else:
            answers.append({**answer, 'value': 'black' if code == 'math_lesson' else 'green'})
    answers.append({'question_code': 'custom_house_description', 'text': ' Домик для кота '})
    run = _run({**example, 'answers': answers})

    assert run.error is None
    result = run.output
    assert result['result']['vegetative_coefficient']['value'] == 0.93  # (18 − 3 − 1) / (18 − 1 − 2)
    assert result['result']['self_esteem']['value'] == 'positive'
    math = next(d for d in result['domains'] if d['code'] == 'math_lesson')
    assert math['status'] == 'attention' and math['title'] == 'Урок математики'
    custom = next(d for d in result['domains'] if d['code'] == 'custom_house')
    assert custom['description'] == 'Домик для кота'
