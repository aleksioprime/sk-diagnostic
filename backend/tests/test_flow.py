"""Выдача классу, прохождение учеником, расчёт, результаты и права."""

from io import BytesIO

import pytest
from openpyxl import load_workbook
from sk_common.testing import login_as

from tests.conftest import other_client
from tests.helpers import login_psychologist, login_student, motivation_test, ranking_test, school_class

pytestmark = pytest.mark.usefixtures('redis_clean')


async def _assign(db, client, test, study_class) -> dict:
    response = await client.post('/api/v1/assignments', json={'test_id': test.id, 'class_id': study_class.id})
    assert response.status_code == 201, response.text
    return response.json()


async def test_psychologist_assigns_class(db, client):
    await login_psychologist(db, client)
    test = await motivation_test(db)
    study_class, _ = await school_class(db)

    classes = (await client.get('/api/v1/classes')).json()
    assert [(c['name'], c['students_count']) for c in classes] == [('7В', 3)]
    tests = (await client.get('/api/v1/tests')).json()
    assert tests[0]['needs_birth_date'] is True and tests[0]['questions_count'] == 40

    assignment = await _assign(db, client, test, study_class)
    assert assignment['title'] == 'Диагностика мотивации учения — 7В'
    assert assignment['total'] == 3 and assignment['assigned'] == 3
    assert [a['student']['full_name'] for a in assignment['attempts']][0] == 'Ученик1 Тест'


async def test_student_passes_motivation(db, client):
    await login_psychologist(db, client)
    test = await motivation_test(db)
    study_class, students = await school_class(db)
    assignment = await _assign(db, client, test, study_class)

    async with other_client(client) as pupil:
        await login_student(db, pupil, students[0])
        mine = (await pupil.get('/api/v1/my/attempts')).json()
        assert len(mine) == 1 and mine[0]['needs_birth_date'] is True
        attempt_id = mine[0]['id']

        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={})).status_code == 400
        started = await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={'birth_date': '2013-03-10'})
        assert started.status_code == 200 and started.json()['status'] == 'in_progress'
        questions = started.json()['questions']
        assert len(questions) == 40 and len(questions[0]['scale_options']) == 4

        # Не на все вопросы — отправить нельзя
        first = questions[0]
        answer = {'scale_option_id': first['scale_options'][1]['id']}
        assert (
            await pupil.put(f'/api/v1/my/attempts/{attempt_id}/answers/{first["id"]}', json=answer)
        ).status_code == 200
        incomplete = await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')
        assert incomplete.status_code == 400 and len(incomplete.json()['detail']['question_ids']) == 39

        wrong = await pupil.put(f'/api/v1/my/attempts/{attempt_id}/answers/{first["id"]}', json={'scale_option_id': 1})
        assert wrong.status_code == 400

        for question in questions:
            option = question['scale_options'][(question['order'] % 4)]
            await pupil.put(
                f'/api/v1/my/attempts/{attempt_id}/answers/{question["id"]}', json={'scale_option_id': option['id']}
            )
        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')).status_code == 204
        done = (await pupil.get('/api/v1/my/attempts')).json()[0]
        assert done['status'] == 'submitted' and done['is_open'] is False
        # Ученик не видит результат и не может ничего поменять
        again = await pupil.put(f'/api/v1/my/attempts/{attempt_id}/answers/{first["id"]}', json=answer)
        assert again.status_code == 409
        assert (await pupil.get(f'/api/v1/attempts/{attempt_id}')).status_code == 403

    detail = (await client.get(f'/api/v1/attempts/{attempt_id}')).json()
    assert detail['result_status'] == 'calculated'
    assert detail['result']['student']['age'] == 13
    assert {s['code'] for s in detail['result']['scales']} == {
        'cognitive_activity',
        'achievement_motivation',
        'anxiety',
        'anger',
    }
    assert detail['summary']['Уровень'].startswith(detail['result']['result']['level'])
    assert detail['answers'][0]['answer'] in ('Почти никогда', 'Иногда', 'Часто', 'Почти всегда')

    overview = (await client.get(f'/api/v1/assignments/{assignment["id"]}')).json()
    assert overview['submitted'] == 1 and overview['assigned'] == 2

    export = await client.get(f'/api/v1/assignments/{assignment["id"]}/export.xlsx')
    rows = list(load_workbook(BytesIO(export.content))['Результаты'].values)
    assert rows[0][:3] == ('№', 'Ученик', 'Класс') and 'Уровень' in rows[0]
    assert rows[1][4] == 'Завершена'


async def test_ranking_must_be_complete(db, client):
    await login_psychologist(db, client)
    test = await ranking_test(db)
    study_class, students = await school_class(db, students=1)
    await _assign(db, client, test, study_class)
    async with other_client(client) as pupil:
        await login_student(db, pupil, students[0])
        attempt_id = (await pupil.get('/api/v1/my/attempts')).json()[0]['id']
        started = (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={})).json()
        question = started['questions'][0]
        ids = [o['id'] for o in question['options']]
        url = f'/api/v1/my/attempts/{attempt_id}/answers/{question["id"]}'
        assert (await pupil.put(url, json={'ranking': [ids[0], ids[0]]})).status_code == 400
        assert (await pupil.put(url, json={'ranking': ids[:2]})).json()['ranking_ids'] == ids[:2]
        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')).status_code == 400
        await pupil.put(url, json={'ranking': list(reversed(ids))})
        assert (await pupil.post(f'/api/v1/my/attempts/{attempt_id}/submit')).status_code == 204

    # Для этой методики нет расчёта — ошибка видна психологу, попытка завершена
    detail = (await client.get(f'/api/v1/attempts/{attempt_id}')).json()
    assert detail['result_status'] == 'error' and 'нет расчёта' in detail['result_error']


async def test_new_students_and_removal(db, client):
    await login_psychologist(db, client)
    test = await motivation_test(db)
    study_class, students = await school_class(db, students=2)
    assignment = await _assign(db, client, test, study_class)

    from sk_common.people.models import Person

    db.add(Person(last_name='Новенький', first_name='Тест', is_student=True, class_id=study_class.id))
    await db.commit()
    synced = (await client.post(f'/api/v1/assignments/{assignment["id"]}/sync')).json()
    assert synced['total'] == 3

    newcomer = next(a for a in synced['attempts'] if a['student']['full_name'] == 'Новенький Тест')
    assert (await client.delete(f'/api/v1/attempts/{newcomer["id"]}')).status_code == 204

    async with other_client(client) as pupil:
        await login_student(db, pupil, students[0])
        attempt_id = (await pupil.get('/api/v1/my/attempts')).json()[0]['id']
        await pupil.post(f'/api/v1/my/attempts/{attempt_id}/start', json={'birth_date': '2013-01-01'})
    assert (await client.delete(f'/api/v1/attempts/{attempt_id}')).status_code == 409

    closed = (await client.patch(f'/api/v1/assignments/{assignment["id"]}', json={'is_active': False})).json()
    assert closed['is_active'] is False
    async with other_client(client) as pupil:
        await login_student(db, pupil, students[1])
        assert (await pupil.get('/api/v1/my/attempts')).json() == []


async def test_access_rules(db, client):
    await login_as(db, client, email='teacher@example.org')
    assert (await client.get('/api/v1/assignments')).status_code == 403
    assert (await client.get('/api/v1/auth/me')).json()['is_psychologist'] is False
    assert (await client.get('/api/v1/psychologists')).status_code == 403

    async with other_client(client) as admin_client:
        await login_as(db, admin_client, email='admin@example.org', is_superuser=True)
        teacher = await admin_client.get('/api/v1/directory/employees', params={'q': 'teacher'})
        assert teacher.status_code == 200
        from sk_common.people.models import User
        from sqlalchemy import select

        person_id = await db.scalar(select(User.person_id).where(User.email == 'teacher@example.org'))
        staff = await admin_client.put('/api/v1/psychologists', json={'person_ids': [person_id]})
        assert [p['email'] for p in staff.json()] == ['teacher@example.org']

    assert (await client.get('/api/v1/assignments')).status_code == 200
    assert (await client.get('/api/v1/auth/me')).json()['is_psychologist'] is True
