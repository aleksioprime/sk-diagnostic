"""Скрипты расчёта: песочница, импорт методики из JSON, проверка на лету, расчёт попытки."""

import copy

from sk_common.testing import login_as

from app.scoring.sandbox import run_script
from tests.conftest import other_client
from tests.helpers import login_psychologist, login_student, motivation_test, school_class

SCRIPT = """
const total = data.answers.reduce((sum, a) => sum + (a.scale_option?.score ?? 0), 0)
console.log('сумма', total)
return { total, summary: { 'Сумма баллов': total, 'Подробно': { total } } }
"""

FILE = {
    'code': 'short_survey',
    'title': 'Короткий опрос',
    'needs_birth_date': False,
    'scoring_script': SCRIPT,
    'scales': [
        {
            'code': 'short_scale',
            'title': 'Шкала',
            'options': [{'label': 'Нет', 'value': '1', 'score': 1}, {'label': 'Да', 'value': '2', 'score': 2}],
        }
    ],
    'questions': [
        {'text': 'Первый', 'question_type': 'scale', 'scale': 'short_scale'},
        {'text': 'Второй', 'question_type': 'scale', 'scale': 'short_scale'},
        {
            'text': 'Выбор',
            'question_type': 'single_choice',
            'options': [{'label': 'А', 'value': 'a'}, {'label': 'Б', 'value': 'b'}],
        },
    ],
}


async def _admin(db, client):
    return await login_as(db, client, email='admin@example.org', is_superuser=True)


async def _import(client, file=FILE, **extra):
    return await client.post('/api/v1/admin/tests/import', json={'test': file, **extra})


def test_sandbox_returns_result_logs_and_accepts_nocobase_format():
    run = run_script("console.log('x', data.a); return { a: data.a + 1 }", {'a': 1})
    assert run.output == {'a': 2} and run.logs == ['x 1'] and run.error is None
    assert run_script("return { status: 'calculated', json: { a: 1 } }", {}).output == {'a': 1}


def test_sandbox_reports_errors_with_script_lines():
    assert run_script("const a = 1\nthrow new Error('boom')", {}).line == 2
    assert run_script("const a = 1\nthrow new Error('boom')", {}).error == 'Error: boom'
    assert run_script('const a = 1\nconst = 2', {}).line == 2
    assert 'объект' in run_script('const a = 1', {}).error


def test_sandbox_stops_endless_and_greedy_scripts_and_has_no_outside_access():
    assert 'остановлен' in run_script('while (true) {}', {}).error
    assert 'памяти' in run_script('const a = []; while (true) a.push(new Array(1e7).fill(1))', {}).error
    run = run_script('return { kinds: [typeof require, typeof process, typeof fetch] }', {})
    assert run.output == {'kinds': ['undefined', 'undefined', 'undefined']}


async def test_admin_only(db, redis_clean, client):
    await login_psychologist(db, client)
    assert (await client.get('/api/v1/admin/tests')).status_code == 403
    assert (await _import(client)).status_code == 403


async def test_import_export_roundtrip_and_replace(db, redis_clean, client):
    await _admin(db, client)
    response = await _import(client)
    assert response.status_code == 201, response.text
    created = response.json()
    assert created['scoring'] == 'script' and created['questions_count'] == 3

    assert (await _import(client)).status_code == 409
    exported = (await client.get(f'/api/v1/admin/tests/{created["id"]}/export')).json()
    assert [q['order'] for q in exported['questions']] == [1, 2, 3]
    assert exported['questions'][0]['scale'] == 'short_scale'
    assert exported['scoring_script'] == SCRIPT

    assert (await _import(client, exported, replace=True)).status_code == 201


async def test_import_rejects_bad_files(db, redis_clean, client):
    await _admin(db, client)
    typo = copy.deepcopy(FILE) | {'titel': 'опечатка'}
    assert (await _import(client, typo)).status_code == 422
    no_scale = copy.deepcopy(FILE) | {'scales': []}
    assert 'short_scale' in (await _import(client, no_scale)).json()['detail']
    await motivation_test(db)
    builtin = copy.deepcopy(FILE) | {'code': 'motivation_learning'}
    assert (await _import(client, builtin)).status_code == 409


async def test_other_scale_with_same_code_is_not_overwritten(db, redis_clean, client):
    await _admin(db, client)
    await _import(client)
    other = copy.deepcopy(FILE) | {'code': 'other_survey'}
    other['scales'][0]['options'][0]['score'] = 5
    response = await _import(client, other)
    assert response.status_code == 409 and 'short_scale' in response.json()['detail']


async def test_run_on_sample_input_saves_nothing(db, redis_clean, client):
    await _admin(db, client)
    test_id = (await _import(client)).json()['id']
    sample = (await client.get(f'/api/v1/admin/tests/{test_id}/sample-input', params={'mode': 'last'})).json()
    assert len(sample['answers']) == 3 and sample['answers'][0]['scale_option']['score'] == 2

    run = (await client.post(f'/api/v1/admin/tests/{test_id}/run', json={'script': SCRIPT, 'input': sample})).json()
    assert run['output']['total'] == 4 and run['logs'] == ['сумма 4']
    assert run['summary']['Сумма баллов'] == 4 and run['summary']['Подробно'] == '{"total": 4}'

    bad = (await client.post(f'/api/v1/admin/tests/{test_id}/run', json={'script': 'throw 1', 'input': {}})).json()
    assert bad['error'] and bad['output'] is None
    assert (await client.get(f'/api/v1/admin/tests/{test_id}')).json()['scoring_script'] == SCRIPT


async def test_builtin_scoring_can_be_tried_but_not_replaced(db, redis_clean, client):
    await _admin(db, client)
    test = await motivation_test(db)
    url = f'/api/v1/admin/tests/{test.id}'
    assert (await client.get(url)).json()['scoring'] == 'builtin'
    assert (await client.put(f'{url}/script', json={'script': 'return {a: 1}'})).status_code == 409
    sample = (await client.get(f'{url}/sample-input', params={'mode': 'first'})).json()
    run = (await client.post(f'{url}/run', json={'input': sample})).json()
    assert run['error'] is None and run['output']['result']['total_score'] is not None
    assert (await client.post(f'{url}/run', json={'input': {'answers': 1}})).json()['error']


async def test_attempt_is_scored_by_script_and_recalculated_after_fix(db, redis_clean, client):
    await _admin(db, client)
    created = (await _import(client)).json()
    assert created['is_active'] is False
    assert (await client.patch(f'/api/v1/admin/tests/{created["id"]}', json={'is_active': True})).status_code == 200
    broken = {'script': 'throw new Error("черновик")'}
    assert (await client.put(f'/api/v1/admin/tests/{created["id"]}/script', json=broken)).status_code == 200
    study_class, persons = await school_class(db, students=1)
    # Администратор и психолог в одном лице: суперпользователю доступны и выдачи
    assignment = (
        await client.post('/api/v1/assignments', json={'test_id': created['id'], 'class_id': study_class.id})
    ).json()
    attempt_id = assignment['attempts'][0]['id']

    async with other_client(client) as pupil:
        await login_student(db, pupil, persons[0])
        attempt = (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={})).json()
        for question in attempt['questions']:
            body = (
                {'scale_option_id': question['scale_options'][1]['id']}
                if question['question_type'] == 'scale'
                else {'option_id': question['options'][0]['id']}
            )
            saved = await pupil.put(f'/api/v1/my/attempts/{attempt_id}/answers/{question["id"]}', json=body)
            assert saved.status_code == 200, saved.text
        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')).status_code == 204

    failed = (await client.get(f'/api/v1/attempts/{attempt_id}')).json()
    assert failed['result_status'] == 'error' and 'черновик' in failed['result_error']

    saved = await client.put(f'/api/v1/admin/tests/{created["id"]}/script', json={'script': SCRIPT})
    assert saved.json()['scoring'] == 'script'
    recalculated = (await client.post(f'/api/v1/attempts/{attempt_id}/recalculate')).json()
    assert recalculated['result']['total'] == 4 and recalculated['summary']['Сумма баллов'] == 4
