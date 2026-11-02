"""Ученик: свои диагностики, прохождение. Результаты ученику не показываются — их смотрит психолог."""

from fastapi import APIRouter, Response
from sk_common.deps import CurrentUser, Db
from sk_common.security import now_utc

from app.modules.attempts import service
from app.modules.attempts.models import STATUS_SUBMITTED, Attempt
from app.modules.attempts.schemas import (
    AnswerIn,
    AnswerOut,
    MyAttemptBrief,
    MyAttemptOut,
    OptionOut,
    QuestionOut,
    ScaleOptionOut,
    StartIn,
    TestOut,
)

router = APIRouter(prefix='/v1/my/attempts', tags=['my'])


def _brief(attempt: Attempt) -> dict:
    assignment = attempt.assignment
    test = assignment.test
    is_open = assignment.is_active and not (assignment.closes_at and now_utc() > assignment.closes_at)
    return {
        'id': attempt.id,
        'status': attempt.status,
        'assignment_title': assignment.title,
        'test': TestOut.model_validate(test),
        'started_at': attempt.started_at,
        'submitted_at': attempt.submitted_at,
        'is_open': is_open and attempt.status != STATUS_SUBMITTED,
        'needs_birth_date': service.needs_birth_date(test) and attempt.person.birth_date is None,
    }


def question_out(question) -> QuestionOut:
    fields = {
        name: getattr(question, name) for name in QuestionOut.model_fields if name not in ('options', 'scale_options')
    }
    return QuestionOut(
        **fields,
        options=[OptionOut.model_validate(o) for o in question.options if o.is_active],
        scale_options=[ScaleOptionOut.model_validate(o) for o in question.scale.options if o.is_active]
        if question.scale
        else [],
    )


def _full(attempt: Attempt) -> MyAttemptOut:
    test = attempt.assignment.test
    questions = [question_out(q) for q in test.questions if q.is_active]
    answers = [AnswerOut.model_validate(a) for a in attempt.answers] if attempt.status != STATUS_SUBMITTED else []
    return MyAttemptOut(**_brief(attempt), questions=questions, answers=answers)


@router.get('', response_model=list[MyAttemptBrief], summary='Мои диагностики')
async def my_attempts(db: Db, user: CurrentUser) -> list[MyAttemptBrief]:
    return [MyAttemptBrief(**_brief(a)) for a in await service.my_attempts(db, user)]


@router.get('/{attempt_id}', response_model=MyAttemptOut, summary='Диагностика с вопросами')
async def my_attempt(attempt_id: int, db: Db, user: CurrentUser) -> MyAttemptOut:
    return _full(await service.my_attempt(db, user, attempt_id))


@router.post('/{attempt_id}/start', response_model=MyAttemptOut, summary='Начать или продолжить')
async def start(attempt_id: int, payload: StartIn, db: Db, user: CurrentUser) -> MyAttemptOut:
    attempt = await service.my_attempt(db, user, attempt_id)
    await service.start(db, attempt, payload.birth_date)
    await db.commit()
    await db.refresh(attempt, ['answers'])
    return _full(attempt)


@router.put('/{attempt_id}/answers/{question_id}', response_model=AnswerOut, summary='Сохранить ответ')
async def save_answer(attempt_id: int, question_id: int, payload: AnswerIn, db: Db, user: CurrentUser) -> AnswerOut:
    attempt = await service.my_attempt(db, user, attempt_id)
    answer = await service.save_answer(db, attempt, question_id, payload)
    await db.commit()
    await db.refresh(answer, ['ranking'])
    return AnswerOut.model_validate(answer)


@router.post('/{attempt_id}/submit', status_code=204, summary='Завершить и отправить')
async def submit(attempt_id: int, db: Db, user: CurrentUser) -> Response:
    attempt = await service.my_attempt(db, user, attempt_id)
    await service.submit(db, attempt)
    await db.commit()
    return Response(status_code=204)
