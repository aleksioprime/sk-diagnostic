"""Редактор методик: создание, копирование, вопросы и шкалы, запреты для уже выданных методик."""

from sk_common.testing import login_as

from tests.helpers import login_psychologist, motivation_test, school_class

BASE = '/api/v1/admin/tests'


async def _admin(db, client):
    return await login_as(db, client, email='admin@example.org', is_superuser=True)


async def _create(client, code='new_test'):
    response = await client.post(BASE, json={'code': code, 'title': 'Новая'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def _body(content, questions=None):
    return {
        'title': content['title'],
        'description': content['description'],
        'is_sequential': content['is_sequential'],
        'questions': content['questions'] if questions is None else questions,
    }


CHOICE = {
    'text': 'Выбор',
    'question_type': 'single_choice',
    'options': [{'label': 'А', 'value': 'a', 'score': 1}, {'label': 'Б', 'value': 'b', 'score': 2}],
}


async def _with_question(client, test_id):
    content = (await client.get(f'{BASE}/{test_id}/content')).json()
    questions = [CHOICE, {'text': 'Текст', 'question_type': 'text'}]
    saved = await client.put(f'{BASE}/{test_id}/content', json=_body(content, questions))
    assert saved.status_code == 200, saved.text
    return saved.json()


async def test_admin_only(db, redis_clean, client):
    await login_psychologist(db, client)
    assert (await client.post(BASE, json={'code': 'x', 'title': 'X'})).status_code == 403


async def test_new_test_is_off_until_it_has_questions(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _create(client)
    assert (await client.get(f'{BASE}/{test_id}')).json()['is_active'] is False
    assert (await client.post(BASE, json={'code': 'new_test', 'title': 'Y'})).status_code == 409
    assert (await client.patch(f'{BASE}/{test_id}', json={'is_active': True})).status_code == 400

    await _with_question(client, test_id)
    assert (await client.patch(f'{BASE}/{test_id}', json={'is_active': True})).json()['is_active'] is True
    content = (await client.get(f'{BASE}/{test_id}/content')).json()
    assert (await client.put(f'{BASE}/{test_id}/content', json=_body(content, []))).status_code == 400


async def test_add_change_reorder_remove_keeps_ids(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _create(client)
    content = await _with_question(client, test_id)
    first, second = content['questions']
    assert content['mode'] == 'full' and first['id'] and first['options'][0]['id']

    first['text'] = 'Изменён'
    first['options'][0]['score'] = 10
    first['options'] = [first['options'][1], first['options'][0], {'label': 'В', 'value': 'c'}]
    third = {'text': 'Да или нет', 'question_type': 'yes_no'}
    saved = (await client.put(f'{BASE}/{test_id}/content', json=_body(content, [second, first, third]))).json()
    assert [q['text'] for q in saved['questions']] == ['Текст', 'Изменён', 'Да или нет']
    assert saved['questions'][0]['id'] == second['id'] and saved['questions'][1]['id'] == first['id']
    assert [o['label'] for o in saved['questions'][1]['options']] == ['Б', 'А', 'В']
    assert saved['questions'][1]['options'][1]['score'] == 10
    sample = (await client.get(f'{BASE}/{test_id}/sample-input', params={'mode': 'first'})).json()
    assert [a['question_number'] for a in sample['answers']] == [1, 2, 3]

    saved = (await client.put(f'{BASE}/{test_id}/content', json=_body(saved, saved['questions'][:1]))).json()
    assert len(saved['questions']) == 1


async def test_bad_questions_rejected(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _create(client)
    content = (await client.get(f'{BASE}/{test_id}/content')).json()
    for question in (
        {'text': 'Шкала', 'question_type': 'scale'},
        {'text': 'Варианты', 'question_type': 'ranking'},
        {'text': 'Несколько', 'question_type': 'multiple_choice'},
        {'id': 1, 'text': 'Чужой', 'question_type': 'text'},
    ):
        response = await client.put(f'{BASE}/{test_id}/content', json=_body(content, [question]))
        assert response.status_code == 400 and 'Вопрос 1' in response.json()['detail']


async def test_issued_test_allows_only_texts(db, redis_clean, client):
    await _admin(db, client)
    test_id = await _create(client)
    content = await _with_question(client, test_id)
    await client.patch(f'{BASE}/{test_id}', json={'is_active': True})
    study_class, _ = await school_class(db, students=1)
    assignment = {'test_id': test_id, 'class_id': study_class.id}
    assert (await client.post('/api/v1/assignments', json=assignment)).status_code == 201

    locked = (await client.get(f'{BASE}/{test_id}/content')).json()
    assert locked['mode'] == 'text' and 'выдавали' in locked['lock_reason']

    locked['title'] = 'Без опечатки'
    locked['questions'][0]['text'] = 'Выбор исправлен'
    locked['questions'][0]['options'][0]['label'] = 'А исправлено'
    saved = await client.put(f'{BASE}/{test_id}/content', json=_body(locked))
    assert saved.status_code == 200 and saved.json()['title'] == 'Без опечатки'
    assert saved.json()['questions'][0]['options'][0]['label'] == 'А исправлено'
    ids = [q['id'] for q in saved.json()['questions']]
    assert ids == [q['id'] for q in content['questions']]

    async def fresh():
        return await client.get(f'{BASE}/{test_id}/content')

    changes = [
        lambda c: c['questions'].reverse(),
        lambda c: c['questions'].pop(),
        lambda c: c['questions'].append({'text': 'Ещё', 'question_type': 'text'}),
        lambda c: c['questions'][0].update(question_type='ranking'),
        lambda c: c['questions'][0].update(is_required=False),
        lambda c: c['questions'][0]['options'][0].update(score=99),
        lambda c: c['questions'][0]['options'][0].update(value='z'),
        lambda c: c['questions'][0]['options'].pop(),
        lambda c: c['questions'][0]['options'].append({'label': 'Новый'}),
    ]
    for change in changes:
        current = (await fresh()).json()
        change(current)
        assert (await client.put(f'{BASE}/{test_id}/content', json=_body(current))).status_code == 409
    final = (await fresh()).json()
    assert len(final['questions']) == 2 and final['questions'][0]['options'][0]['score'] == 1


async def test_builtin_allows_only_texts(db, redis_clean, client):
    await _admin(db, client)
    test = await motivation_test(db)
    content = (await client.get(f'{BASE}/{test.id}/content')).json()
    assert content['mode'] == 'text' and 'встроен' in content['lock_reason']
    assert content['scales'][0]['mode'] == 'text'
    scale = content['scales'][0]
    scale['options'][0]['label'] = 'Редко'
    url = f'{BASE}/{test.id}/scales/{scale["id"]}'
    assert (await client.put(url, json=scale)).json()['options'][0]['label'] == 'Редко'
    scale['options'][0]['score'] = 9
    assert (await client.put(url, json=scale)).status_code == 409


async def test_scale_shared_with_other_test_is_protected(db, redis_clean, client):
    await _admin(db, client)
    first, second = await _create(client, 'first'), await _create(client, 'second')
    options = [{'label': 'Нет', 'value': '0', 'score': 0}, {'label': 'Да', 'value': '1', 'score': 1}]
    created = (await client.post(f'{BASE}/{first}/scales', json={'title': 'Шкала', 'options': options})).json()
    question = {'text': 'С', 'question_type': 'scale', 'scale_id': created['id']}
    for test_id in (first, second):
        content = (await client.get(f'{BASE}/{test_id}/content')).json()
        assert (await client.put(f'{BASE}/{test_id}/content', json=_body(content, [question]))).status_code == 200
    content = (await client.get(f'{BASE}/{first}/content')).json()
    assert content['scales'][0]['mode'] == 'none'
    response = await client.put(f'{BASE}/{first}/scales/{created["id"]}', json={'title': 'Другая', 'options': options})
    assert response.status_code == 409


async def test_copy_is_independent_and_keeps_scoring(db, redis_clean, client):
    await _admin(db, client)
    source = await motivation_test(db)
    study_class, _ = await school_class(db, students=1)
    assignment = {'test_id': source.id, 'class_id': study_class.id}
    assert (await client.post('/api/v1/assignments', json=assignment)).status_code == 201

    new = {'code': 'motivation_v2', 'title': 'Мотивация, версия 2'}
    copied = await client.post(f'{BASE}/{source.id}/copy', json=new)
    assert copied.status_code == 201, copied.text
    detail = copied.json()
    assert detail['is_active'] is False and detail['scoring'] == 'script' and detail['needs_birth_date'] is True
    assert detail['assignments_count'] == 0 and detail['questions_count'] == 40
    assert 'function' in detail['scoring_script']
    assert (await client.post(f'{BASE}/{source.id}/copy', json=new)).status_code == 409

    content = (await client.get(f'{BASE}/{detail["id"]}/content')).json()
    assert content['mode'] == 'full'
    original = (await client.get(f'{BASE}/{source.id}/content')).json()
    own = next(s for s in content['scales'] if s['id'] == content['questions'][0]['scale_id'])
    assert own['id'] != original['questions'][0]['scale_id'] and own['mode'] == 'full'

    own['options'][0]['score'] = 100
    assert (await client.put(f'{BASE}/{detail["id"]}/scales/{own["id"]}', json=own)).status_code == 200
    content['questions'][0]['text'] = 'Новая формулировка'
    assert (await client.put(f'{BASE}/{detail["id"]}/content', json=_body(content))).status_code == 200

    after = (await client.get(f'{BASE}/{source.id}/content')).json()
    assert after['questions'][0]['text'] == original['questions'][0]['text']
    scale = next(s for s in after['scales'] if s['id'] == after['questions'][0]['scale_id'])
    assert scale['options'][0]['score'] == 1

    sample = (await client.get(f'{BASE}/{detail["id"]}/sample-input', params={'mode': 'first'})).json()
    body = {'script': detail['scoring_script'], 'input': sample}
    run = (await client.post(f'{BASE}/{detail["id"]}/run', json=body)).json()
    assert run['error'] is None and run['summary']


async def test_copy_takes_script_from_database(db, redis_clean, client):
    await _admin(db, client)
    source = await _create(client)
    await _with_question(client, source)
    script = 'return { total: 1 }'
    assert (await client.put(f'{BASE}/{source}/script', json={'script': script})).status_code == 200

    copy = (await client.post(f'{BASE}/{source}/copy', json={'code': 'copy_test', 'title': 'Копия'})).json()
    assert copy['scoring'] == 'script' and copy['scoring_script'] == script

    # У копии свой скрипт: правка не доходит до исходной методики
    await client.put(f'{BASE}/{copy["id"]}/script', json={'script': 'return { total: 2 }'})
    assert (await client.get(f'{BASE}/{source}')).json()['scoring_script'] == script
