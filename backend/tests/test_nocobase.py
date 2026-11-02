"""Перенос из NocoBase: ID сохраняются, дата рождения переносится, заготовки ответов не переносятся."""

import json
import uuid

import pytest
from sk_common.people.models import Person
from sqlalchemy import func, select

from app.legacy.nocobase import load
from app.modules.attempts.models import Answer, Attempt, Result

pytestmark = pytest.mark.usefixtures('redis_clean')

STUDENT = str(uuid.uuid4())


def _data() -> dict:
    scale_options = [
        {'id': 20 + n, 'scale_id': 10, 'label': f'{n}', 'value': str(n), 'score': n, 'order': n} for n in range(1, 5)
    ]
    questions = [
        {'id': 100 + n, 'test_id': 30, 'order': n, 'text': f'Вопрос {n}', 'question_type': 'scale', 'scale_id': 10}
        for n in range(1, 41)
    ]
    answers = [
        {'id': 1000 + n, 'attempt_id': 60, 'question_id': 100 + n, 'scale_option_id': 20 + (n % 4) + 1}
        for n in range(1, 41)
    ]
    answers.append({'id': 2000, 'attempt_id': 61, 'question_id': 101})  # заготовка без ответа
    return {
        'persons': [
            {
                'id': 5,
                'last_name': 'Иванова',
                'first_name': 'Анна',
                'skolstream_id': STUDENT,
                'birth_date': '2012-09-23',
                'gender': 'female',
            },
            {'id': 6, 'last_name': 'Без', 'first_name': 'UUID'},
        ],
        'scales': [{'id': 10, 'title': 'Частота', 'code': 'freq_1_4'}],
        'scale_options': scale_options,
        'tests': [{'id': 30, 'title': 'Мотивация', 'code': 'motivation_learning', 'is_sequential': True}],
        'questions': questions,
        'options': [],
        'test_assignments': [{'id': 40, 'test_id': 30, 'title': '7В', 'public_token': 'odc14q3x', 'is_active': False}],
        'attempts': [
            {
                'id': 60,
                'test_assignment_id': 40,
                'person_id': 5,
                'status': 'submitted',
                'submitted_at': '2026-05-25T10:12:05.903Z',
            },
            {'id': 61, 'test_assignment_id': 40, 'person_id': 6, 'status': 'assigned'},
        ],
        'answers': answers,
        'answer_ranking_items': [],
        'attempt_results': [],
    }


@pytest.fixture
def source(tmp_path):
    for name, rows in _data().items():
        (tmp_path / f'{name}.json').write_text(json.dumps(rows, ensure_ascii=False))
    return tmp_path


async def test_load(db, source):
    report = await load(db, source)
    await db.commit()
    assert report['counts']['answers'] == 40 and report['counts']['results'] == 1
    assert [s['reason'] for s in report['skipped']['attempts']] == ['ученик не сопоставлен со SkolStream']

    person = await db.scalar(select(Person).where(Person.skolstream_id == uuid.UUID(STUDENT)))
    assert person.birth_date.isoformat() == '2012-09-23'
    attempt = await db.get(Attempt, 60)
    assert attempt.person_id == person.id and attempt.assignment.public_token == 'odc14q3x'
    result = await db.scalar(select(Result).where(Result.attempt_id == 60))
    assert result.status == 'calculated' and result.data['student']['age'] == 13

    again = await load(db, source)
    await db.commit()
    assert again['counts'] == {}
    assert await db.scalar(select(func.count(Answer.id))) == 40
