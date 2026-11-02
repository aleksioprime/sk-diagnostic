"""Выдачи методик и результаты — для психологов."""

import secrets
import string
from collections import Counter
from io import BytesIO

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from sk_common.people.models import Person, StudyClass, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attempts.models import STATUS_ASSIGNED, Assignment, Attempt
from app.modules.tests.models import Test

TOKEN_ALPHABET = string.ascii_lowercase + string.digits


def not_found(message: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, message)


async def class_students(db: AsyncSession, class_id: int) -> list[Person]:
    rows = await db.scalars(
        select(Person)
        .where(Person.class_id == class_id, Person.is_active.is_(True), Person.is_student.is_(True))
        .order_by(Person.last_name, Person.first_name)
    )
    return list(rows.unique())


async def _new_token(db: AsyncSession) -> str:
    while True:
        token = ''.join(secrets.choice(TOKEN_ALPHABET) for _ in range(10))
        if not await db.scalar(select(Assignment.id).where(Assignment.public_token == token)):
            return token


async def create_assignment(db: AsyncSession, user: User, test_id: int, class_id: int, title: str) -> Assignment:
    test = await db.get(Test, test_id)
    if test is None or not test.is_active:
        raise not_found('Методика не найдена')
    study_class = await db.get(StudyClass, class_id)
    if study_class is None:
        raise not_found('Класс не найден')
    assignment = Assignment(
        test_id=test.id,
        class_id=study_class.id,
        title=title.strip() or f'{test.title} — {study_class.name}',
        public_token=await _new_token(db),
        created_by_id=user.id,
    )
    db.add(assignment)
    await db.flush()
    await add_students(db, assignment, [p.id for p in await class_students(db, study_class.id)])
    return assignment


async def add_students(db: AsyncSession, assignment: Assignment, person_ids: list[int]) -> int:
    """Попытки для учеников, которых ещё нет в выдаче. Возвращает, сколько добавлено."""
    existing = set(await db.scalars(select(Attempt.person_id).where(Attempt.assignment_id == assignment.id)))
    added = 0
    for person_id in dict.fromkeys(person_ids):
        if person_id not in existing:
            db.add(Attempt(assignment_id=assignment.id, person_id=person_id))
            added += 1
    await db.flush()
    return added


async def sync_class(db: AsyncSession, assignment: Assignment) -> int:
    """Новые ученики класса (пришли после выдачи) получают свою попытку."""
    if assignment.class_id is None:
        return 0
    return await add_students(db, assignment, [p.id for p in await class_students(db, assignment.class_id)])


async def remove_attempt(db: AsyncSession, attempt: Attempt) -> None:
    if attempt.status != STATUS_ASSIGNED:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Ученик уже начал диагностику — удалить нельзя')
    await db.delete(attempt)
    await db.flush()


async def status_counts(db: AsyncSession, assignment_ids: list[int]) -> dict[int, Counter]:
    counts: dict[int, Counter] = {i: Counter() for i in assignment_ids}
    if assignment_ids:
        rows = await db.execute(
            select(Attempt.assignment_id, Attempt.status, func.count())
            .where(Attempt.assignment_id.in_(assignment_ids))
            .group_by(Attempt.assignment_id, Attempt.status)
        )
        for assignment_id, state, count in rows.all():
            counts[assignment_id][state] = count
    return counts


async def assignment_attempts(db: AsyncSession, assignment_id: int) -> list[Attempt]:
    rows = await db.scalars(
        select(Attempt)
        .join(Person, Person.id == Attempt.person_id)
        .where(Attempt.assignment_id == assignment_id)
        .order_by(Person.last_name, Person.first_name)
    )
    return list(rows.unique())


# --- Краткий итог для таблиц и выгрузки -----------------------------------------------------


def summary(data: dict | None) -> dict[str, str]:
    """Главные показатели результата одной строкой на ученика. Формат зависит от методики."""
    if not data:
        return {}
    result = data.get('result') or {}
    if 'level' in result:  # мотивация учения
        items = {
            'Уровень': f'{result["level"]} — {result.get("level_description", "")}',
            'Сумма баллов': result.get('total_score'),
            'Интерпретация': result.get('interpretation'),
        }
        for scale in data.get('scales') or []:
            items[scale['title']] = f'{scale["value"]} ({scale["level_label"]})'
        return items
    items = {
        'Вегетативный коэффициент': _value_label(result.get('vegetative_coefficient')),
        'Эмоциональный фон': _value_label(result.get('emotional_background'), 'title'),
        'Самооценка': (result.get('self_esteem') or {}).get('label'),
        'Отношение к школе': (result.get('school_relation') or {}).get('label'),
    }
    attention = [d['title'] for d in data.get('domains') or [] if d.get('status') == 'attention']
    items['Обратить внимание'] = ', '.join(attention) or 'нет'
    return items


def _value_label(item: dict | None, key: str = 'label') -> str | None:
    if not item:
        return None
    return f'{item.get("value")} — {item.get(key)}'


STATUS_TITLES = {'assigned': 'Не начата', 'in_progress': 'Начата', 'submitted': 'Завершена'}


def export_xlsx(assignment: Assignment, attempts: list[Attempt]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = 'Результаты'
    summaries = [summary(a.result.data if a.result else None) for a in attempts]
    keys = list(dict.fromkeys(key for item in summaries for key in item))
    header = ['№', 'Ученик', 'Класс', 'Дата рождения', 'Статус', 'Завершена', *keys, 'Ошибка расчёта']
    sheet.append(header)
    for number, (attempt, items) in enumerate(zip(attempts, summaries, strict=True), 1):
        person = attempt.person
        sheet.append(
            [
                number,
                person.full_name,
                person.study_class.name if person.study_class else '',
                person.birth_date,
                STATUS_TITLES.get(attempt.status, attempt.status),
                attempt.submitted_at.astimezone().replace(tzinfo=None) if attempt.submitted_at else None,
                *[items.get(key) for key in keys],
                attempt.result.error if attempt.result and attempt.result.error else None,
            ]
        )
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    widths = [5, 32, 8, 14, 12, 18] + [28] * len(keys) + [30]
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = 'C2'
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
