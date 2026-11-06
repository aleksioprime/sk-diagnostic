"""Проверка готовности перед включением и предпросмотр глазами ученика."""

from sk_common.people.models import PERSON_SOURCE_SKOLSTREAM, Person
from sk_common.testing import login_as
from sqlalchemy import func, select

from app.modules.attempts.models import Answer, Attempt, Result
from tests.conftest import other_client
from tests.helpers import login_psychologist, motivation_test, school_class

BASE = '/api/v1/admin/tests'
SCORE = 'const total = data.answers[0].selected_option?.score ?? 0\nreturn { total, summary: { Балл: total } }'
CHOICE = {
    'text': 'Выбор',
    'question_type': 'single_choice',
    'options': [{'label': 'А', 'value': 'a', 'score': 1}, {'label': 'Б', 'value': 'b', 'score': 2}],
}
FILE = {'code': 'ready', 'title': 'Готовность', 'scoring_script': SCORE, 'questions': [CHOICE]}


async def _admin(db, client):
    return await login_as(db, client, email='admin@example.org', is_superuser=True)


async def _import(client, **changes):
    response = await client.post(f'{BASE}/import', json={'test': FILE | changes})
    assert response.status_code == 201, response.text
    return response.json()['id']


async def _problems(client, test_id):
    answer = (await client.get(f'{BASE}/{test_id}/readiness')).json()
    return answer['ready'], answer['problems']


async def test_good_test_is_ready_and_enabled(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client)
    assert await _problems(client, test_id) == (True, [])
    assert (await client.patch(f'{BASE}/{test_id}', json={'is_active': True})).json()['is_active'] is True


async def test_errors_block_enabling(db, redis_clean, client):
    await _admin(db, client)
    cases = {
        'Нет расчёта': {'scoring_script': None},
        'падает': {'scoring_script': 'throw new Error("сломано")'},
        'хотя бы два': {'questions': [CHOICE | {'options': CHOICE['options'][:1]}]},
    }
    for number, (expected, changes) in enumerate(cases.items()):
        test_id = await _import(client, code=f'bad_{number}', **changes)
        ready, problems = await _problems(client, test_id)
        assert ready is False and any(expected in p['text'] for p in problems), problems
        response = await client.patch(f'{BASE}/{test_id}', json={'is_active': True})
        assert response.status_code == 400 and expected in response.json()['detail']


async def test_script_error_names_line(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client, scoring_script='const a = 1\nthrow new Error("сломано")')
    _, problems = await _problems(client, test_id)
    assert 'строка 2' in problems[0]['text'] and problems[0]['tab'] == 'scoring'


async def test_warnings_do_not_block(db, redis_clean, client):
    await _admin(db, client)
    no_values = [{'label': 'А'}, {'label': 'Б', 'value': 'b'}, {'label': 'В', 'value': 'b'}]
    test_id = await _import(
        client,
        scoring_script='return { total: 1 }',
        questions=[CHOICE | {'options': no_values}, {'text': 'выбор', 'question_type': 'text'}],
    )
    ready, problems = await _problems(client, test_id)
    texts = ' | '.join(p['text'] for p in problems)
    assert ready is True and {p['level'] for p in problems} == {'warning'}
    for expected in ('ни значения', 'повторяются', 'такой же текст', 'summary', 'не использует ответы'):
        assert expected in texts
    assert (await client.patch(f'{BASE}/{test_id}', json={'is_active': True})).status_code == 200


async def test_builtin_is_checked_too(db, redis_clean, client):
    await _admin(db, client)
    test = await motivation_test(db)
    ready, problems = await _problems(client, test.id)
    assert ready is True and not [p for p in problems if p['tab'] == 'scoring']


async def test_test_without_scoring_cannot_be_issued(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client, scoring_script=None)
    # Старая включённая методика без расчёта: включить её теперь нельзя, но такие могли остаться
    from app.modules.tests.models import Test

    test = await db.get(Test, test_id)
    test.is_active = True
    await db.commit()
    study_class, _ = await school_class(db, students=1)
    await login_psychologist(db, client)
    assert (await client.get('/api/v1/tests')).json() == []
    response = await client.post('/api/v1/assignments', json={'test_id': test_id, 'class_id': study_class.id})
    assert response.status_code == 400 and 'нет расчёта' in response.json()['detail']


async def test_preview_shows_questions_and_saves_nothing(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client)
    preview = (await client.get(f'{BASE}/{test_id}/preview')).json()
    assert preview['test']['title'] == 'Готовность' and preview['needs_birth_date'] is False
    question = preview['questions'][0]
    second = question['options'][1]['id']

    body = {'answers': [{'question_id': question['id'], 'option_id': second}]}
    run = (await client.post(f'{BASE}/{test_id}/preview/result', json=body)).json()
    assert run['error'] is None and run['output']['total'] == 2 and run['summary'] == {'Балл': 2}

    for model in (Attempt, Answer, Result):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_preview_rejects_foreign_answers_and_reports_missing_scoring(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client, scoring_script=None)
    question = (await client.get(f'{BASE}/{test_id}/preview')).json()['questions'][0]
    url = f'{BASE}/{test_id}/preview/result'
    assert (await client.post(url, json={'answers': [{'question_id': 1}]})).status_code == 400
    wrong = {'answers': [{'question_id': question['id'], 'option_id': 1}]}
    assert (await client.post(url, json=wrong)).status_code == 400
    run = (await client.post(url, json={'answers': []})).json()
    assert 'нет расчёта' in run['error']


async def test_preview_uses_birth_date_for_builtin(db, redis_clean, client):
    await _admin(db, client)
    test = await motivation_test(db)
    preview = (await client.get(f'{BASE}/{test.id}/preview')).json()
    assert preview['needs_birth_date'] is True and len(preview['questions']) == 40
    answers = [{'question_id': q['id'], 'scale_option_id': q['scale_options'][1]['id']} for q in preview['questions']]
    body = {'answers': answers, 'birth_date': '2014-03-10'}
    run = (await client.post(f'{BASE}/{test.id}/preview/result', json=body)).json()
    assert run['error'] is None and run['output']['result']['total_score'] is not None


async def test_student_outside_skolstream_passes_issued_test(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _import(client)
    assert (await client.patch(f'{BASE}/{test_id}', json={'is_active': True})).status_code == 200
    study_class, _ = await school_class(db, students=1)
    created = await client.post(
        '/api/v1/people/users',
        json={'email': 'guest@example.org', 'full_name': 'Гостева Анна', 'password': 'fixture-pass-123'},
    )
    assert created.status_code == 201, created.text
    person_id = created.json()['person']['id']

    assignment = await client.post('/api/v1/assignments', json={'test_id': test_id, 'class_id': study_class.id})
    assignment_id = assignment.json()['id']
    assert (await client.get('/api/v1/students', params={'q': 'Гостева'})).json() == []
    marked = await client.put(f'/api/v1/persons/{person_id}/student', json={'is_student': True})
    assert marked.status_code == 200
    assert len((await client.get('/api/v1/students', params={'q': 'Гостева'})).json()) == 1
    added = await client.post(f'/api/v1/assignments/{assignment_id}/students', json={'person_ids': [person_id]})
    attempt_id = next(a['id'] for a in added.json()['attempts'] if a['student']['person_id'] == person_id)

    async with other_client(client) as pupil:
        credentials = {'email': 'guest@example.org', 'password': 'fixture-pass-123'}
        login = await pupil.post('/api/v1/auth/login', json=credentials)
        assert login.status_code == 200, login.text
        started = (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={})).json()
        question = started['questions'][0]
        answer = {'option_id': question['options'][1]['id']}
        await pupil.put(f'/api/v1/my/attempts/{attempt_id}/answers/{question["id"]}', json=answer)
        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')).status_code == 204
        assert (await pupil.get(f'/api/v1/attempts/{attempt_id}')).status_code == 403

    detail = (await client.get(f'/api/v1/attempts/{attempt_id}')).json()
    assert detail['result']['total'] == 2 and detail['summary'] == {'Балл': 2}


async def test_skolstream_student_flag_is_not_changed_by_hand(db, redis_clean, client):
    await _admin(db, client)
    person = Person(last_name='Из', first_name='Школы', email='s@example.org', source=PERSON_SOURCE_SKOLSTREAM)
    db.add(person)
    await db.commit()
    response = await client.put(f'/api/v1/persons/{person.id}/student', json={'is_student': True})
    assert response.status_code == 409
