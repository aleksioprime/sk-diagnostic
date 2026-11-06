"""Импорт и выгрузка методик, пример входных данных для проверки расчёта."""

import random
from datetime import UTC, date, datetime
from types import SimpleNamespace

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import scoring
from app.modules.attempts.models import Assignment
from app.modules.attempts.scoring_input import build_input
from app.modules.tests.models import Option, Question, Scale, ScaleOption, Test
from app.modules.tests.schemas import ScaleFile, TestFile


def scoring_kind(test: Test) -> str:
    if test.scoring_script:
        return 'script'
    return 'builtin' if test.code in scoring.CALCULATORS else 'none'


async def assignments_count(db: AsyncSession, test_id: int) -> int:
    return await db.scalar(select(func.count()).select_from(Assignment).where(Assignment.test_id == test_id)) or 0


def check_script_allowed(code: str, script: str | None) -> None:
    """Встроенные методики сверены с результатами NocoBase: скрипт не должен их подменять."""
    if script and code in scoring.CALCULATORS:
        raise HTTPException(status.HTTP_409_CONFLICT, f'У методики {code} встроенный расчёт, скрипт ей задать нельзя')


# --- Импорт ---------------------------------------------------------------------------------


def _option_key(items) -> list[tuple]:
    return [(o.label, o.value, o.score) for o in items]


async def _resolve_scales(db: AsyncSession, file: TestFile) -> dict[str, Scale]:
    """Шкалы по коду: из файла или уже существующие. Чужую шкалу с тем же кодом незаметно не меняем."""
    described: dict[str, ScaleFile] = {s.code: s for s in file.scales}
    if len(described) != len(file.scales):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Коды шкал в файле повторяются')
    codes = set(described) | {q.scale for q in file.questions if q.scale}
    existing = {s.code: s for s in await db.scalars(select(Scale).where(Scale.code.in_(codes)))} if codes else {}
    scales: dict[str, Scale] = {}
    for code in sorted(codes):
        known, new = existing.get(code), described.get(code)
        if known is None and new is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Шкала {code} не описана в файле и не найдена в базе')
        if known is not None and new is not None and _option_key(known.options) != _option_key(new.options):
            raise HTTPException(status.HTTP_409_CONFLICT, f'Шкала {code} уже есть в базе с другими вариантами')
        scales[code] = known or Scale(
            code=code,
            title=new.title,
            description=new.description,
            options=[
                ScaleOption(label=o.label, description=o.description, value=o.value, score=o.score, order=n)
                for n, o in enumerate(new.options, 1)
            ],
        )
    return scales


async def import_test(db: AsyncSession, file: TestFile, replace: bool) -> Test:
    check_script_allowed(file.code, file.scoring_script)
    test = await db.scalar(select(Test).where(Test.code == file.code))
    if test is not None:
        if not replace:
            raise HTTPException(status.HTTP_409_CONFLICT, f'Методика с кодом {file.code} уже есть')
        if await assignments_count(db, test.id):
            # Замена вопросов удалила бы ответы учеников
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f'Методику {file.code} уже выдавали классам: вопросы менять нельзя, загрузите её с новым кодом',
            )
        await db.delete(test)
        await db.flush()
    scales = await _resolve_scales(db, file)
    test = Test(
        code=file.code,
        title=file.title,
        description=file.description,
        is_sequential=file.is_sequential,
        needs_birth_date=file.needs_birth_date,
        scoring_script=file.scoring_script or None,
    )
    test.questions = [
        Question(
            order=q.order if q.order is not None else number,
            code=q.code,
            text=q.text,
            description=q.description,
            question_type=q.question_type,
            is_required=q.is_required,
            is_random=q.is_random,
            min_selections=q.min_selections,
            max_selections=q.max_selections,
            scale=scales[q.scale] if q.scale else None,
            options=[
                Option(label=o.label, description=o.description, value=o.value, score=o.score, order=n)
                for n, o in enumerate(q.options, 1)
            ],
        )
        for number, q in enumerate(file.questions, 1)
    ]
    db.add(test)
    await db.flush()
    return test


def _options_file(options) -> list[dict]:
    return [
        {'label': o.label, 'description': o.description, 'value': o.value, 'score': o.score}
        for o in options
        if o.is_active
    ]


def _scale_code(scale: Scale) -> str:
    """У шкал из NocoBase кода может не быть, а файл ссылается на шкалу по коду."""
    return scale.code or f'scale_{scale.id}'


def export_test(test: Test) -> dict:
    questions = [q for q in test.questions if q.is_active]
    scales = {_scale_code(q.scale): q.scale for q in questions if q.scale}
    return {
        'code': test.code,
        'title': test.title,
        'description': test.description,
        'is_sequential': test.is_sequential,
        'needs_birth_date': test.needs_birth_date,
        'scoring_script': test.scoring_script,
        'scales': [
            {'code': code, 'title': s.title, 'description': s.description, 'options': _options_file(s.options)}
            for code, s in scales.items()
        ],
        'questions': [
            {
                'order': q.order,
                'code': q.code,
                'text': q.text,
                'description': q.description,
                'question_type': q.question_type,
                'is_required': q.is_required,
                'is_random': q.is_random,
                'min_selections': q.min_selections,
                'max_selections': q.max_selections,
                'scale': _scale_code(q.scale) if q.scale else None,
                'options': _options_file(q.options),
            }
            for q in questions
        ],
    }


# --- Пример входных данных ------------------------------------------------------------------


def _sample_birth_date() -> date:
    """Ученику примера 12 лет: возраст попадает в нормы методик."""
    today = datetime.now(UTC).date()
    return date(today.year - 12, 1, 15)


def _sample_answer(question: Question, pick) -> SimpleNamespace | None:
    answer = SimpleNamespace(
        question_id=question.id, option_id=None, scale_option_id=None, text=None, number=None, boolean=None, ranking=[]
    )
    options = [o for o in question.options if o.is_active]
    kind = question.question_type
    if kind == 'scale' and question.scale:
        answer.scale_option_id = pick([o for o in question.scale.options if o.is_active]).id
    elif kind == 'single_choice' and options:
        answer.option_id = pick(options).id
    elif kind == 'ranking' and options:
        ordered = random.sample(options, len(options)) if pick is random.choice else options
        answer.ranking = [SimpleNamespace(rank=n, option_id=o.id) for n, o in enumerate(ordered, 1)]
    elif kind == 'text':
        answer.text = 'Пример ответа'
    elif kind == 'number':
        answer.number = 5
    elif kind == 'yes_no':
        answer.boolean = pick([True, False])
    else:
        return None
    return answer


def sample_input(test: Test, mode: str) -> dict:
    """Входные данные как у настоящей попытки, но с выдуманным учеником: реальные ответы сюда не попадают."""
    pick = {'random': random.choice, 'first': lambda items: items[0], 'last': lambda items: items[-1]}[mode]
    answers = [_sample_answer(q, pick) for q in test.questions if q.is_active]
    person = SimpleNamespace(
        id=0, last_name='Пример', first_name='Ученик', birth_date=_sample_birth_date(), gender='female'
    )
    attempt = SimpleNamespace(id=0, answers=[a for a in answers if a], person=person, submitted_at=datetime.now(UTC))
    return build_input(attempt, test)
