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
from app.modules.tests.schemas import (
    ContentIn,
    ContentOut,
    OptionIn,
    QuestionIn,
    QuestionOut,
    ScaleFile,
    ScaleIn,
    ScaleOut,
    TestCreateIn,
    TestFile,
)

CHOICE_TYPES = ('single_choice', 'ranking')
# multiple_choice не поддерживается формой ученика и хранением ответа
EDITABLE_TYPES = ('single_choice', 'scale', 'ranking', 'text', 'number', 'yes_no')


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


# --- Создание и копирование -----------------------------------------------------------------


async def _check_code_free(db: AsyncSession, code: str) -> None:
    if await db.scalar(select(Test.id).where(Test.code == code)):
        raise HTTPException(status.HTTP_409_CONFLICT, f'Методика с кодом {code} уже есть')


async def create_test(db: AsyncSession, body: TestCreateIn) -> Test:
    """Пустая методика отключена: психологи увидят её, когда администратор её включит."""
    await _check_code_free(db, body.code)
    test = Test(code=body.code, title=body.title, is_active=False, questions=[])
    db.add(test)
    await db.flush()
    return test


async def copy_test(db: AsyncSession, source: Test, body: TestCreateIn) -> Test:
    """Независимая копия: свои вопросы и шкалы, правки не затрагивают исходную методику и её результаты.

    Копия отключена, пока её не проверят. Встроенный расчёт переносится скриптом, который можно менять.
    """
    await _check_code_free(db, body.code)
    scales: dict[int, Scale] = {}

    def copied_scale(scale: Scale) -> Scale:
        if scale.id not in scales:
            scales[scale.id] = Scale(
                code=f'{body.code}__{scale.code or scale.id}'[:100],
                title=scale.title,
                description=scale.description,
                options=[
                    ScaleOption(label=o.label, description=o.description, value=o.value, score=o.score, order=o.order)
                    for o in scale.options
                    if o.is_active
                ],
            )
        return scales[scale.id]

    test = Test(
        code=body.code,
        title=body.title,
        description=source.description,
        is_sequential=source.is_sequential,
        is_active=False,
        needs_birth_date=source.needs_birth_date or source.code in scoring.NEEDS_BIRTH_DATE,
        scoring_script=source.scoring_script or scoring.builtin_script(source.code),
        questions=[
            Question(
                order=q.order,
                code=q.code,
                text=q.text,
                description=q.description,
                question_type=q.question_type,
                is_required=q.is_required,
                is_random=q.is_random,
                min_selections=q.min_selections,
                max_selections=q.max_selections,
                scale=copied_scale(q.scale) if q.scale else None,
                options=[
                    Option(label=o.label, description=o.description, value=o.value, score=o.score, order=o.order)
                    for o in q.options
                    if o.is_active
                ],
            )
            for q in source.questions
            if q.is_active
        ],
    )
    db.add(test)
    await db.flush()
    return test


# --- Редактор вопросов и шкал ---------------------------------------------------------------


async def lock_reason(db: AsyncSession, test: Test) -> str | None:
    """Почему нельзя менять состав и баллы: от них зависят ответы учеников и расчёт."""
    if await assignments_count(db, test.id):
        return 'Методику уже выдавали классам: можно менять только тексты, чтобы результаты остались сопоставимы.'
    if test.code in scoring.CALCULATORS:
        return 'Расчёт встроен в приложение и опирается на номера вопросов и значения: можно менять только тексты.'
    return None


async def _scale_modes(db: AsyncSession, test: Test, locked: bool) -> dict[int, str]:
    used = select(Question.scale_id, Question.test_id).where(Question.scale_id.is_not(None)).distinct()
    rows = await db.execute(used)
    users: dict[int, set[int]] = {}
    for scale_id, test_id in rows:
        users.setdefault(scale_id, set()).add(test_id)
    scales = await db.scalars(select(Scale.id))
    modes = {}
    for scale_id in scales:
        used_by = users.get(scale_id, set())
        if used_by - {test.id}:
            modes[scale_id] = 'none'
        else:
            modes[scale_id] = 'text' if locked and test.id in used_by else 'full'
    return modes


def _options_out(options) -> list[OptionIn]:
    return [
        OptionIn(id=o.id, label=o.label, description=o.description, value=o.value, score=o.score)
        for o in sorted(options, key=lambda item: item.order)
        if o.is_active
    ]


def scale_out(scale: Scale, mode: str) -> ScaleOut:
    return ScaleOut(
        id=scale.id,
        code=scale.code,
        title=scale.title,
        description=scale.description,
        mode=mode,
        options=_options_out(scale.options),
    )


async def content(db: AsyncSession, test: Test) -> ContentOut:
    reason = await lock_reason(db, test)
    modes = await _scale_modes(db, test, reason is not None)
    scales = await db.scalars(select(Scale).where(Scale.is_active.is_(True)).order_by(Scale.title))
    return ContentOut(
        id=test.id,
        code=test.code,
        title=test.title,
        description=test.description,
        is_sequential=test.is_sequential,
        mode='text' if reason else 'full',
        lock_reason=reason,
        questions=[
            QuestionOut(
                id=q.id,
                code=q.code,
                text=q.text,
                description=q.description,
                question_type=q.question_type,
                is_required=q.is_required,
                is_random=q.is_random,
                scale_id=q.scale_id,
                options=_options_out(q.options),
            )
            for q in sorted(test.questions, key=lambda item: item.order)
            if q.is_active
        ],
        scales=[scale_out(s, modes.get(s.id, 'full')) for s in scales.unique()],
    )


def _bad(message: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, message)


def _locked(what: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, f'Изменить можно только тексты: {what}')


def _active_sorted(items) -> list:
    return sorted((item for item in items if item.is_active), key=lambda item: item.order)


def _apply_option_texts(existing: list, incoming: list[OptionIn], place: str) -> None:
    if [o.id for o in incoming] != [o.id for o in existing]:
        raise _locked(f'{place} — состав и порядок вариантов менять нельзя')
    for item, new in zip(existing, incoming, strict=True):
        if item.value != new.value or item.score != new.score:
            raise _locked(f'{place} — значения и баллы менять нельзя')
        item.label, item.description = new.label, new.description


def _sync_options(owner, incoming: list[OptionIn], factory, place: str) -> None:
    """Варианты как на форме: новые создаются, убранные удаляются, отключённые из NocoBase не трогаем."""
    known = {o.id: o for o in owner.options if o.is_active}
    kept = []
    for number, new in enumerate(incoming, 1):
        if new.id is not None and new.id not in known:
            raise _bad(f'{place}: вариант {new.id} не найден')
        item = known[new.id] if new.id is not None else factory()
        item.label, item.description, item.value, item.score = new.label, new.description, new.value, new.score
        item.order = number
        kept.append(item)
    owner.options = kept + [o for o in owner.options if not o.is_active]


def _check_question(new: QuestionIn, number: int, previous: Question | None, scale_ids: set[int]) -> None:
    place = f'Вопрос {number}'
    unchanged = previous is not None and previous.question_type == new.question_type
    if new.question_type not in EDITABLE_TYPES and not unchanged:
        raise _bad(f'{place}: тип {new.question_type} не поддерживается')
    if new.question_type == 'scale' and new.scale_id not in scale_ids:
        raise _bad(f'{place}: выберите шкалу')
    if new.question_type in CHOICE_TYPES and not new.options:
        raise _bad(f'{place}: добавьте варианты ответа')


def _apply_question_texts(test: Test, body: ContentIn) -> None:
    existing = _active_sorted(test.questions)
    if [q.id for q in body.questions] != [q.id for q in existing]:
        raise _locked('состав и порядок вопросов менять нельзя')
    for number, (question, new) in enumerate(zip(existing, body.questions, strict=True), 1):
        place = f'вопрос {number}'
        if (
            question.question_type != new.question_type
            or question.scale_id != new.scale_id
            or question.is_required != new.is_required
            or question.is_random != new.is_random
            or question.code != new.code
        ):
            raise _locked(f'{place} — тип, шкалу, код и обязательность менять нельзя')
        question.text, question.description = new.text, new.description
        _apply_option_texts(_active_sorted(question.options), new.options, place)


async def _sync_questions(db: AsyncSession, test: Test, body: ContentIn) -> None:
    if test.is_active and not body.questions:
        raise _bad('В включённой методике должен быть хотя бы один вопрос: сначала отключите её')
    known = {q.id: q for q in test.questions if q.is_active}
    scale_ids = set(await db.scalars(select(Scale.id)))
    kept = []
    for number, new in enumerate(body.questions, 1):
        if new.id is not None and new.id not in known:
            raise _bad(f'Вопрос {number}: не найден в этой методике')
        question = known[new.id] if new.id is not None else Question(test_id=test.id, options=[])
        _check_question(new, number, known.get(new.id), scale_ids)
        question.order = number
        question.code = new.code or None
        question.text, question.description = new.text, new.description
        question.question_type = new.question_type
        question.is_required, question.is_random = new.is_required, new.is_random
        question.scale_id = new.scale_id if new.question_type == 'scale' else None
        options = new.options if new.question_type in CHOICE_TYPES else []
        _sync_options(question, options, Option, f'Вопрос {number}')
        kept.append(question)
    test.questions = kept + [q for q in test.questions if not q.is_active]


async def save_content(db: AsyncSession, test: Test, body: ContentIn) -> None:
    test.title, test.description, test.is_sequential = body.title, body.description, body.is_sequential
    if await lock_reason(db, test):
        _apply_question_texts(test, body)
    else:
        await _sync_questions(db, test, body)
    await db.flush()


async def create_scale(db: AsyncSession, body: ScaleIn) -> Scale:
    scale = Scale(title=body.title, description=body.description, options=[])
    _sync_options(scale, body.options, ScaleOption, 'Шкала')
    db.add(scale)
    await db.flush()
    return scale


async def save_scale(db: AsyncSession, test: Test, scale: Scale, body: ScaleIn) -> str:
    """Шкалу меняем только в той мере, в какой это не задевает ответы и другие методики."""
    reason = await lock_reason(db, test)
    mode = (await _scale_modes(db, test, reason is not None)).get(scale.id, 'full')
    if mode == 'none':
        raise HTTPException(
            status.HTTP_409_CONFLICT, 'Шкалу используют и другие методики: создайте для этой методики свою'
        )
    scale.title, scale.description = body.title, body.description
    if mode == 'text':
        _apply_option_texts(_active_sorted(scale.options), body.options, 'шкала')
    else:
        _sync_options(scale, body.options, ScaleOption, 'Шкала')
    await db.flush()
    return mode


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
