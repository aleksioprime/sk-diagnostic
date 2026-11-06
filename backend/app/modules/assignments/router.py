"""Психологическая служба: методики, выдачи классам, результаты, выгрузка."""

from datetime import date
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response, status
from sk_common.audit import record
from sk_common.deps import AdminUser, Db
from sk_common.people.models import PERSON_SOURCE_SKOLSTREAM, AcademicYear, Person, StudyClass, User
from sk_common.people.service import ensure_user, normalize_email
from sk_common.security import hash_password
from sqlalchemy import func, or_, select

from app.modules.assignments import service
from app.modules.assignments.schemas import (
    AddStudentsIn,
    AnswerView,
    AssignmentDetail,
    AssignmentIn,
    AssignmentOut,
    AssignmentPatch,
    AttemptDetail,
    AttemptRow,
    BirthDateIn,
    ClassOut,
    PersonEditIn,
    PersonEditOut,
    PsychologistOut,
    PsychologistsIn,
    StudentOut,
)
from app.modules.attempts import service as attempts_service
from app.modules.attempts.models import STATUS_SUBMITTED, Assignment, Attempt
from app.modules.attempts.schemas import TestBrief
from app.modules.staff.models import Psychologist
from app.modules.staff.permissions import PsychologistUser
from app.modules.tests.models import Question, Test

router = APIRouter(prefix='/v1', tags=['psychologists'])

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


# --- Справочники ----------------------------------------------------------------------------


@router.get('/tests', response_model=list[TestBrief], summary='Методики')
async def list_tests(db: Db, _: PsychologistUser) -> list[TestBrief]:
    tests = list(await db.scalars(select(Test).where(Test.is_active.is_(True)).order_by(Test.title)))
    return [
        TestBrief.model_validate(t).model_copy(
            update={
                'questions_count': len([q for q in t.questions if q.is_active]),
                'needs_birth_date': attempts_service.needs_birth_date(t),
            }
        )
        for t in tests
        if attempts_service.has_scoring(t)
    ]


@router.get('/classes', response_model=list[ClassOut], summary='Классы текущего учебного года')
async def list_classes(db: Db, _: PsychologistUser) -> list[ClassOut]:
    counts = dict(
        (
            await db.execute(
                select(Person.class_id, func.count())
                .where(Person.is_active.is_(True), Person.is_student.is_(True))
                .group_by(Person.class_id)
            )
        ).all()
    )
    rows = await db.scalars(
        select(StudyClass)
        .outerjoin(AcademicYear, AcademicYear.id == StudyClass.academic_year_id)
        .where(
            StudyClass.is_active.is_(True),
            or_(AcademicYear.is_current.is_(True), StudyClass.academic_year_id.is_(None)),
        )
        .order_by(StudyClass.grade, StudyClass.letter)
    )
    return [
        ClassOut(
            id=c.id,
            name=c.name,
            grade=c.grade,
            academic_year=c.academic_year.name if c.academic_year else None,
            students_count=counts.get(c.id, 0),
        )
        for c in rows.unique()
    ]


@router.get('/students', response_model=list[StudentOut], summary='Найти ученика')
async def search_students(
    db: Db, _: PsychologistUser, q: Annotated[str, Query(min_length=2, max_length=100)]
) -> list[StudentOut]:
    pattern = f'%{q.strip()}%'
    rows = await db.scalars(
        select(Person)
        .where(
            Person.is_student.is_(True),
            Person.is_active.is_(True),
            or_(Person.last_name.ilike(pattern), Person.first_name.ilike(pattern)),
        )
        .order_by(Person.last_name, Person.first_name)
        .limit(20)
    )
    return [_student(p) for p in rows.unique()]


async def _external_person(db, person_id: int) -> Person:
    person = await db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Человек не найден')
    if person.source == PERSON_SOURCE_SKOLSTREAM:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Данные этого человека приходят из SkolStream')
    return person


def _person_edit_out(person: Person, user: User | None) -> PersonEditOut:
    return PersonEditOut(
        id=person.id,
        last_name=person.last_name,
        first_name=person.first_name,
        middle_name=person.middle_name,
        email=person.email,
        gender=person.gender,
        birth_date=person.birth_date,
        class_id=person.class_id,
        is_student=person.is_student,
        is_employee=person.is_employee,
        has_account=user is not None,
        has_password=bool(user and user.password_hash),
    )


async def _person_user(db, person: Person) -> User | None:
    return await db.scalar(select(User).where(User.person_id == person.id))


@router.get('/persons/{person_id}', response_model=PersonEditOut, summary='Человек не из SkolStream')
async def get_person(person_id: int, db: Db, _: AdminUser) -> PersonEditOut:
    person = await _external_person(db, person_id)
    return _person_edit_out(person, await _person_user(db, person))


@router.patch('/persons/{person_id}', response_model=PersonEditOut, summary='Изменить человека не из SkolStream')
async def edit_person(person_id: int, payload: PersonEditIn, db: Db, admin: AdminUser) -> PersonEditOut:
    person = await _external_person(db, person_id)
    user = await _person_user(db, person)
    changes = payload.model_dump(exclude_unset=True)
    password = changes.pop('password', None)
    if changes.get('class_id') is not None and await db.get(StudyClass, changes['class_id']) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Класс не найден')

    if 'email' in changes:
        email = normalize_email(changes['email']) if changes['email'] else None
        if email is None and user is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'У учётной записи должен быть email')
        taken = await db.scalar(select(User).where(User.email == email)) if email else None
        if taken is not None and taken.id != (user.id if user else None):
            raise HTTPException(status.HTTP_409_CONFLICT, 'Этот email уже занят другой учётной записью')
        changes['email'] = email
        if user is not None:
            user.email = email
    for name in ('last_name', 'first_name', 'middle_name'):
        if name in changes:
            changes[name] = (changes[name] or '').strip()
    for name in ('is_student', 'is_employee'):
        if name in changes and changes[name] is None:
            changes.pop(name)
    for name, value in changes.items():
        setattr(person, name, value)

    if password:
        if user is None:
            if not person.email:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Чтобы задать пароль, укажите email')
            user = await ensure_user(db, person, person.email)
        user.password_hash = hash_password(password)
    # Значения в журнал не пишем: это личные данные
    record(db, 'person.update', 'person', person.id, admin.id, fields=sorted(changes), password_set=bool(password))
    await db.commit()
    return _person_edit_out(person, user)


def _student(person: Person) -> StudentOut:
    return StudentOut(
        person_id=person.id,
        full_name=person.full_name,
        class_name=person.study_class.name if person.study_class else None,
        birth_date=person.birth_date,
        gender=person.gender,
    )


@router.put('/persons/{person_id}/birth-date', response_model=StudentOut, summary='Исправить дату рождения')
async def set_birth_date(person_id: int, payload: BirthDateIn, db: Db, user: PsychologistUser) -> StudentOut:
    person = await db.get(Person, person_id)
    if person is None or not person.is_student:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Ученик не найден')
    if payload.birth_date and not date(1990, 1, 1) <= payload.birth_date <= date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Проверьте дату рождения')
    person.birth_date = payload.birth_date
    record(db, 'person.birth_date', 'person', person.id, user.id)
    await db.commit()
    return _student(person)


# --- Выдачи ---------------------------------------------------------------------------------


def _assignment_out(assignment: Assignment, counts) -> AssignmentOut:
    return AssignmentOut(
        id=assignment.id,
        title=assignment.title,
        test_id=assignment.test_id,
        test_title=assignment.test.title,
        test_code=assignment.test.code,
        needs_birth_date=attempts_service.needs_birth_date(assignment.test),
        class_id=assignment.class_id,
        class_name=assignment.study_class.name if assignment.study_class else None,
        is_active=assignment.is_active,
        closes_at=assignment.closes_at,
        created_at=assignment.created_at,
        total=sum(counts.values()),
        assigned=counts.get('assigned', 0),
        in_progress=counts.get('in_progress', 0),
        submitted=counts.get('submitted', 0),
    )


def _row(attempt: Attempt) -> AttemptRow:
    result = attempt.result
    return AttemptRow(
        id=attempt.id,
        status=attempt.status,
        student=_student(attempt.person),
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        duration=attempt.duration,
        result_status=result.status if result else None,
        result_error=result.error if result else None,
        summary=service.summary(result.data if result else None),
    )


async def _assignment(db, assignment_id: int) -> Assignment:
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Выдача не найдена')
    return assignment


async def _detail(db, assignment: Assignment) -> AssignmentDetail:
    counts = (await service.status_counts(db, [assignment.id]))[assignment.id]
    attempts = await service.assignment_attempts(db, assignment.id)
    return AssignmentDetail(**_assignment_out(assignment, counts).model_dump(), attempts=[_row(a) for a in attempts])


@router.get('/assignments', response_model=list[AssignmentOut], summary='Выдачи методик')
async def list_assignments(db: Db, _: PsychologistUser) -> list[AssignmentOut]:
    rows = list((await db.scalars(select(Assignment).order_by(Assignment.created_at.desc()))).unique())
    counts = await service.status_counts(db, [a.id for a in rows])
    return [_assignment_out(a, counts[a.id]) for a in rows]


@router.post('/assignments', response_model=AssignmentDetail, status_code=201, summary='Выдать методику классу')
async def create_assignment(payload: AssignmentIn, db: Db, user: PsychologistUser) -> AssignmentDetail:
    assignment = await service.create_assignment(db, user, payload.test_id, payload.class_id, payload.title)
    record(db, 'assignment.create', 'assignment', assignment.id, user.id, test_id=payload.test_id)
    await db.commit()
    return await _detail(db, assignment)


@router.get('/assignments/{assignment_id}', response_model=AssignmentDetail, summary='Выдача с учениками')
async def get_assignment(assignment_id: int, db: Db, _: PsychologistUser) -> AssignmentDetail:
    return await _detail(db, await _assignment(db, assignment_id))


@router.patch('/assignments/{assignment_id}', response_model=AssignmentDetail, summary='Изменить выдачу')
async def update_assignment(
    assignment_id: int, payload: AssignmentPatch, db: Db, user: PsychologistUser
) -> AssignmentDetail:
    assignment = await _assignment(db, assignment_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    record(
        db,
        'assignment.update',
        'assignment',
        assignment.id,
        user.id,
        **payload.model_dump(exclude_unset=True, mode='json'),
    )
    await db.commit()
    return await _detail(db, assignment)


@router.post(
    '/assignments/{assignment_id}/sync', response_model=AssignmentDetail, summary='Добавить новых учеников класса'
)
async def sync_class(assignment_id: int, db: Db, _: PsychologistUser) -> AssignmentDetail:
    assignment = await _assignment(db, assignment_id)
    await service.sync_class(db, assignment)
    await db.commit()
    return await _detail(db, assignment)


@router.post('/assignments/{assignment_id}/students', response_model=AssignmentDetail, summary='Добавить учеников')
async def add_students(assignment_id: int, payload: AddStudentsIn, db: Db, _: PsychologistUser) -> AssignmentDetail:
    assignment = await _assignment(db, assignment_id)
    found = set(
        await db.scalars(select(Person.id).where(Person.id.in_(payload.person_ids), Person.is_student.is_(True)))
    )
    if found != set(payload.person_ids):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Ученик не найден')
    await service.add_students(db, assignment, payload.person_ids)
    await db.commit()
    return await _detail(db, assignment)


@router.post(
    '/assignments/{assignment_id}/recalculate', response_model=AssignmentDetail, summary='Пересчитать результаты'
)
async def recalculate_assignment(assignment_id: int, db: Db, user: PsychologistUser) -> AssignmentDetail:
    assignment = await _assignment(db, assignment_id)
    for attempt in await service.assignment_attempts(db, assignment.id):
        if attempt.status == STATUS_SUBMITTED:
            await attempts_service.calculate(db, attempt)
    record(db, 'assignment.recalculate', 'assignment', assignment.id, user.id)
    await db.commit()
    return await _detail(db, assignment)


@router.get('/assignments/{assignment_id}/export.xlsx', summary='Результаты в Excel')
async def export(assignment_id: int, db: Db, user: PsychologistUser) -> Response:
    assignment = await _assignment(db, assignment_id)
    content = service.export_xlsx(assignment, await service.assignment_attempts(db, assignment.id))
    record(db, 'assignment.export', 'assignment', assignment.id, user.id)
    await db.commit()
    filename = quote(f'{assignment.title[:80]}.xlsx')
    return Response(
        content, media_type=XLSX, headers={'Content-Disposition': f"attachment; filename*=UTF-8''{filename}"}
    )


# --- Попытки --------------------------------------------------------------------------------


async def _attempt(db, attempt_id: int) -> Attempt:
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Попытка не найдена')
    return attempt


def _answer_text(question: Question, answer) -> str | None:
    if answer is None:
        return None
    options = {o.id: o.label for o in question.options}
    if answer.ranking:
        return ', '.join(f'{item.rank}. {options.get(item.option_id, "?")}' for item in answer.ranking)
    if answer.scale_option_id and question.scale:
        return next((o.label for o in question.scale.options if o.id == answer.scale_option_id), None)
    if answer.option_id:
        return options.get(answer.option_id)
    if answer.boolean is not None:
        return 'Да' if answer.boolean else 'Нет'
    if answer.number is not None:
        return f'{answer.number:g}'
    return answer.text


@router.get('/attempts/{attempt_id}', response_model=AttemptDetail, summary='Попытка: ответы и результат')
async def get_attempt(attempt_id: int, db: Db, _: PsychologistUser) -> AttemptDetail:
    attempt = await _attempt(db, attempt_id)
    test = attempt.assignment.test
    by_question = {a.question_id: a for a in attempt.answers}
    answers = [
        AnswerView(
            question_id=q.id,
            order=q.order,
            text=q.text,
            question_type=q.question_type,
            answer=_answer_text(q, by_question.get(q.id)),
        )
        for q in test.questions
        if q.is_active or q.id in by_question
    ]
    return AttemptDetail(
        **_row(attempt).model_dump(),
        assignment_id=attempt.assignment_id,
        assignment_title=attempt.assignment.title,
        test_code=test.code,
        test_title=test.title,
        result=attempt.result.data if attempt.result else None,
        answers=answers,
    )


@router.post('/attempts/{attempt_id}/recalculate', response_model=AttemptDetail, summary='Пересчитать результат')
async def recalculate_attempt(attempt_id: int, db: Db, user: PsychologistUser) -> AttemptDetail:
    attempt = await _attempt(db, attempt_id)
    if attempt.status != STATUS_SUBMITTED:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Ученик ещё не завершил диагностику')
    await attempts_service.calculate(db, attempt)
    record(db, 'attempt.recalculate', 'attempt', attempt.id, user.id)
    await db.commit()
    return await get_attempt(attempt_id, db, user)


@router.delete('/attempts/{attempt_id}', status_code=204, summary='Убрать ученика из выдачи (не начатую попытку)')
async def delete_attempt(attempt_id: int, db: Db, user: PsychologistUser) -> Response:
    attempt = await _attempt(db, attempt_id)
    await service.remove_attempt(db, attempt)
    record(db, 'attempt.delete', 'attempt', attempt_id, user.id)
    await db.commit()
    return Response(status_code=204)


# --- Психологи (назначает администратор) ----------------------------------------------------


async def _psychologists(db) -> list[PsychologistOut]:
    rows = await db.scalars(select(Psychologist))
    return [
        PsychologistOut(
            user_id=p.user.id,
            person_id=p.user.person_id,
            full_name=p.user.person.full_name if p.user.person else p.user.email,
            email=p.user.email,
        )
        for p in rows.unique()
    ]


@router.get('/psychologists', response_model=list[PsychologistOut], summary='Психологическая служба')
async def list_psychologists(db: Db, _: AdminUser) -> list[PsychologistOut]:
    return await _psychologists(db)


@router.put('/psychologists', response_model=list[PsychologistOut], summary='Назначить психологов')
async def set_psychologists(payload: PsychologistsIn, db: Db, admin: AdminUser) -> list[PsychologistOut]:
    persons = list(await db.scalars(select(Person).where(Person.id.in_(payload.person_ids or [0]))))
    if len(persons) != len(set(payload.person_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Сотрудник не найден')
    users: list[User] = []
    for person in persons:
        if not person.email:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'У {person.full_name} нет email')
        users.append(await ensure_user(db, person, person.email))
    current = {p.user_id: p for p in await db.scalars(select(Psychologist))}
    wanted = {u.id for u in users}
    for user_id, item in current.items():
        if user_id not in wanted:
            await db.delete(item)
    for user_id in wanted - set(current):
        db.add(Psychologist(user_id=user_id))
    record(db, 'psychologists.set', 'user', None, admin.id, user_ids=sorted(wanted))
    await db.commit()
    return await _psychologists(db)
