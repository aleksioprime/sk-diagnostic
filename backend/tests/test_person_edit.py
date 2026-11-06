"""Администратор меняет данные людей не из SkolStream; данные из SkolStream приходят только синхронизацией."""

from sk_common.people.models import PERSON_SOURCE_SKOLSTREAM, Person
from sk_common.testing import login_as

from tests.conftest import other_client
from tests.helpers import login_psychologist, school_class


async def _guest(client, password=None):
    body = {'email': 'guest@example.org', 'full_name': 'Гостева'}
    if password:
        body['password'] = password
    created = await client.post('/api/v1/people/users', json=body)
    assert created.status_code == 201, created.text
    return created.json()['person']['id']


async def _admin(db, client):
    return await login_as(db, client, email='admin@example.org', is_superuser=True)


async def test_edit_fields_and_clear_them(db, redis_clean, client):
    await _admin(db, client)
    person_id = await _guest(client)
    study_class, _ = await school_class(db, students=1)
    url = f'/api/v1/persons/{person_id}'

    before = (await client.get(url)).json()
    assert before['last_name'] == 'Гостева' and before['has_account'] is True and before['has_password'] is False

    body = {
        'first_name': ' Анна ',
        'gender': 'female',
        'birth_date': '2012-03-10',
        'class_id': study_class.id,
        'is_student': True,
    }
    saved = (await client.patch(url, json=body)).json()
    assert saved['first_name'] == 'Анна' and saved['last_name'] == 'Гостева'
    assert saved['gender'] == 'female' and saved['class_id'] == study_class.id and saved['is_student'] is True

    cleared = (await client.patch(url, json={'class_id': None, 'birth_date': None})).json()
    assert cleared['class_id'] is None and cleared['birth_date'] is None and cleared['gender'] == 'female'
    assert (await client.patch(url, json={'class_id': 1})).status_code == 400


async def test_password_set_by_admin_allows_login(db, redis_clean, client):
    await _admin(db, client)
    person_id = await _guest(client)
    url = f'/api/v1/persons/{person_id}'
    credentials = {'email': 'guest@example.org', 'password': 'fixture-pass-123'}
    async with other_client(client) as guest:
        assert (await guest.post('/api/v1/auth/login', json=credentials)).status_code != 200

    assert (await client.patch(url, json={'password': 'short'})).status_code == 422
    assert (await client.patch(url, json={'password': credentials['password']})).json()['has_password'] is True
    async with other_client(client) as guest:
        assert (await guest.post('/api/v1/auth/login', json=credentials)).status_code == 200


async def test_email_changes_login_and_cannot_be_taken(db, redis_clean, client):
    await _admin(db, client)
    person_id = await _guest(client, password='fixture-pass-123')
    url = f'/api/v1/persons/{person_id}'

    assert (await client.patch(url, json={'email': 'ADMIN@example.org'})).status_code == 409
    assert (await client.patch(url, json={'email': None})).status_code == 400
    assert (await client.patch(url, json={'email': 'New@Example.org'})).json()['email'] == 'new@example.org'
    async with other_client(client) as guest:
        credentials = {'email': 'new@example.org', 'password': 'fixture-pass-123'}
        assert (await guest.post('/api/v1/auth/login', json=credentials)).status_code == 200


async def test_person_without_account_gets_one_with_password(db, redis_clean, client):
    await _admin(db, client)
    person = Person(last_name='Без', first_name='Учётной')
    db.add(person)
    await db.commit()
    url = f'/api/v1/persons/{person.id}'
    assert (await client.patch(url, json={'password': 'fixture-pass-123'})).status_code == 400
    saved = await client.patch(url, json={'email': 'noacc@example.org', 'password': 'fixture-pass-123'})
    assert saved.json()['has_account'] is True and saved.json()['has_password'] is True


async def test_skolstream_person_is_read_only(db, redis_clean, client):
    await _admin(db, client)
    person = Person(last_name='Из', first_name='Школы', email='s@example.org', source=PERSON_SOURCE_SKOLSTREAM)
    db.add(person)
    await db.commit()
    url = f'/api/v1/persons/{person.id}'
    assert (await client.get(url)).status_code == 409
    assert (await client.patch(url, json={'first_name': 'Другое'})).status_code == 409


async def test_only_admin_edits_people(db, redis_clean, client):
    await login_psychologist(db, client)
    assert (await client.patch('/api/v1/persons/1', json={'first_name': 'Х'})).status_code == 403
