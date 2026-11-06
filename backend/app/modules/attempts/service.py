"""Прохождение методики учеником и расчёт результата."""

from datetime import date

from fastapi import HTTPException, status
from sk_common.people.models import User
from sk_common.security import now_utc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import scoring
from app.modules.attempts.models import (
    RESULT_CALCULATED,
    RESULT_ERROR,
    STATUS_ASSIGNED,
    STATUS_IN_PROGRESS,
    STATUS_SUBMITTED,
    Answer,
    Assignment,
    Attempt,
    RankingItem,
    Result,
)
from app.modules.attempts.schemas import AnswerIn
from app.modules.attempts.scoring_input import build_input
from app.modules.tests.models import Question, Test


def _bad(message: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, message)


def needs_birth_date(test: Test) -> bool:
    return test.needs_birth_date or test.code in scoring.NEEDS_BIRTH_DATE


# --- Ученик ---------------------------------------------------------------------------------


async def my_attempts(db: AsyncSession, user: User) -> list[Attempt]:
    if user.person_id is None:
        return []
    rows = await db.scalars(
        select(Attempt)
        .join(Assignment, Assignment.id == Attempt.assignment_id)
        .where(Attempt.person_id == user.person_id, Assignment.is_active.is_(True))
        .order_by(Attempt.status != STATUS_SUBMITTED, Assignment.created_at.desc())
    )
    return list(rows.unique())


async def my_attempt(db: AsyncSession, user: User, attempt_id: int) -> Attempt:
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None or user.person_id is None or attempt.person_id != user.person_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Диагностика не найдена')
    return attempt


def _check_open(attempt: Attempt) -> None:
    assignment = attempt.assignment
    if not assignment.is_active or (assignment.closes_at and now_utc() > assignment.closes_at):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Диагностика закрыта')
    if attempt.status == STATUS_SUBMITTED:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Ответы уже отправлены')


async def start(db: AsyncSession, attempt: Attempt, birth_date: date | None) -> None:
    _check_open(attempt)
    test = attempt.assignment.test
    person = attempt.person
    if needs_birth_date(test) and person.birth_date is None:
        if birth_date is None:
            raise _bad('Укажите дату рождения: она нужна для расчёта результата')
        if not date(1990, 1, 1) <= birth_date <= date.today():
            raise _bad('Проверьте дату рождения')
        person.birth_date = birth_date
    if attempt.status == STATUS_ASSIGNED:
        attempt.status = STATUS_IN_PROGRESS
        attempt.started_at = now_utc()
    await db.flush()


async def save_answer(db: AsyncSession, attempt: Attempt, question_id: int, data: AnswerIn) -> Answer:
    _check_open(attempt)
    if attempt.status != STATUS_IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Сначала начните диагностику')
    question = await db.get(Question, question_id)
    if question is None or question.test_id != attempt.assignment.test_id or not question.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Вопрос не найден')
    # Сохранения одной попытки идут по очереди: быстрые клики по цветам иначе создают дубли ответа
    await db.execute(select(Attempt.id).where(Attempt.id == attempt.id).with_for_update())

    answer = await db.scalar(select(Answer).where(Answer.attempt_id == attempt.id, Answer.question_id == question.id))
    if answer is None:
        answer = Answer(attempt_id=attempt.id, question_id=question.id)
        db.add(answer)
        await db.flush()
    await db.refresh(answer, ['ranking'])
    answer.option_id = answer.scale_option_id = answer.text = answer.number = answer.boolean = None
    answer.ranking = []

    options = {o.id for o in question.options if o.is_active}
    kind = question.question_type
    if kind == 'scale':
        allowed = {o.id for o in question.scale.options if o.is_active} if question.scale else set()
        if data.scale_option_id is not None and data.scale_option_id not in allowed:
            raise _bad('Такого значения нет')
        answer.scale_option_id = data.scale_option_id
    elif kind == 'single_choice':
        if data.option_id is not None and data.option_id not in options:
            raise _bad('Такого варианта нет')
        answer.option_id = data.option_id
    elif kind == 'ranking':
        ranked = data.ranking
        if len(set(ranked)) != len(ranked) or set(ranked) - options:
            raise _bad('Такого варианта нет')
        answer.ranking = [RankingItem(option_id=oid, rank=rank) for rank, oid in enumerate(ranked, 1)]
    elif kind == 'text':
        answer.text = (data.text or '').strip() or None
    elif kind == 'number':
        answer.number = data.number
    elif kind == 'yes_no':
        answer.boolean = data.boolean
    await db.flush()
    return answer


def is_answered(question: Question, answer: Answer | None) -> bool:
    if answer is None:
        return False
    if question.question_type == 'ranking':
        # Расставить нужно все цвета (варианты) или столько, сколько требует методика
        needed = question.min_selections or len([o for o in question.options if o.is_active])
        return len(answer.ranking) >= needed
    return any(
        value is not None
        for value in (answer.option_id, answer.scale_option_id, answer.text, answer.number, answer.boolean)
    )


async def submit(db: AsyncSession, attempt: Attempt) -> Result:
    _check_open(attempt)
    if attempt.status != STATUS_IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Сначала начните диагностику')
    test = attempt.assignment.test
    await db.refresh(attempt, ['answers'])
    by_question = {a.question_id: a for a in attempt.answers}
    missing = [
        q.id for q in test.questions if q.is_active and q.is_required and not is_answered(q, by_question.get(q.id))
    ]
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, {'message': 'Ответьте на все вопросы', 'question_ids': missing}
        )
    attempt.status = STATUS_SUBMITTED
    attempt.submitted_at = now_utc()
    if attempt.started_at:
        attempt.duration = int((attempt.submitted_at - attempt.started_at).total_seconds())
    await db.flush()
    return await calculate(db, attempt)


# --- Расчёт ---------------------------------------------------------------------------------


async def calculate(db: AsyncSession, attempt: Attempt) -> Result:
    """Пересчитать результат отправленной попытки. Ошибка расчёта сохраняется, психолог видит её."""
    test = attempt.assignment.test
    await db.refresh(attempt, ['answers', 'result'])
    result = attempt.result or Result(attempt_id=attempt.id)
    try:
        result.data = await scoring.calculate_test(test.code, test.scoring_script, build_input(attempt, test))
        result.status, result.error = RESULT_CALCULATED, None
    except scoring.ScoringError as exc:
        result.data, result.status, result.error = None, RESULT_ERROR, str(exc)
    result.calculated_at = now_utc()
    if attempt.result is None:
        db.add(result)
    await db.flush()
    return result
