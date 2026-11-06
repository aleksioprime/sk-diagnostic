"""Администратор: методики, импорт из JSON, скрипт расчёта и его проверка."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sk_common.audit import record
from sk_common.deps import AdminUser, Db
from sqlalchemy import select

from app.modules.assignments.service import summary
from app.modules.attempts.router import question_out
from app.modules.attempts.schemas import TestOut
from app.modules.attempts.service import needs_birth_date
from app.modules.tests import service
from app.modules.tests.models import Scale, Test
from app.modules.tests.schemas import (
    ContentIn,
    ContentOut,
    ImportIn,
    PreviewOut,
    PreviewResultIn,
    ReadinessOut,
    RunIn,
    RunOut,
    ScaleIn,
    ScaleOut,
    ScriptIn,
    TestAdminBrief,
    TestAdminDetail,
    TestCreateIn,
    TestPatch,
)
from app.scoring.sandbox import ScriptRun

router = APIRouter(prefix='/v1/admin/tests', tags=['admin-tests'])


async def _test(db, test_id: int) -> Test:
    test = await db.get(Test, test_id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Методика не найдена')
    return test


async def _brief_fields(db, test: Test) -> dict:
    return {
        'id': test.id,
        'code': test.code,
        'title': test.title,
        'is_active': test.is_active,
        'questions_count': len([q for q in test.questions if q.is_active]),
        'assignments_count': await service.assignments_count(db, test.id),
        'scoring': service.scoring_kind(test),
    }


async def _detail(db, test: Test) -> TestAdminDetail:
    return TestAdminDetail(
        **await _brief_fields(db, test),
        description=test.description,
        needs_birth_date=test.needs_birth_date,
        scoring_script=test.scoring_script,
    )


@router.get('', response_model=list[TestAdminBrief], summary='Все методики')
async def list_tests(db: Db, _: AdminUser) -> list[TestAdminBrief]:
    tests = await db.scalars(select(Test).order_by(Test.title))
    return [TestAdminBrief(**await _brief_fields(db, t)) for t in tests]


@router.post('', response_model=TestAdminDetail, status_code=201, summary='Создать пустую методику')
async def create_test(body: TestCreateIn, db: Db, user: AdminUser) -> TestAdminDetail:
    test = await service.create_test(db, body)
    record(db, 'test.create', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, test)


@router.post('/import', response_model=TestAdminDetail, status_code=201, summary='Загрузить методику из JSON')
async def import_test(body: ImportIn, db: Db, user: AdminUser) -> TestAdminDetail:
    test = await service.import_test(db, body.test, body.replace)
    record(db, 'test.import', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, await _test(db, test.id))


@router.get('/{test_id}', response_model=TestAdminDetail, summary='Методика')
async def get_test(test_id: int, db: Db, _: AdminUser) -> TestAdminDetail:
    return await _detail(db, await _test(db, test_id))


@router.patch('/{test_id}', response_model=TestAdminDetail, summary='Изменить настройки методики')
async def patch_test(test_id: int, body: TestPatch, db: Db, user: AdminUser) -> TestAdminDetail:
    test = await _test(db, test_id)
    if body.is_active and not test.is_active:
        errors = [p.text for p in await service.readiness(test) if p.level == 'error']
        if errors:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f'Методику нельзя включить. {"; ".join(errors[:3])}')
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(test, key, value)
    record(db, 'test.update', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, test)


@router.post('/{test_id}/copy', response_model=TestAdminDetail, status_code=201, summary='Создать копию методики')
async def copy_test(test_id: int, body: TestCreateIn, db: Db, user: AdminUser) -> TestAdminDetail:
    test = await service.copy_test(db, await _test(db, test_id), body)
    record(db, 'test.copy', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, await _test(db, test.id))


@router.get('/{test_id}/content', response_model=ContentOut, summary='Вопросы и шкалы для редактора')
async def get_content(test_id: int, db: Db, _: AdminUser) -> ContentOut:
    return await service.content(db, await _test(db, test_id))


@router.put('/{test_id}/content', response_model=ContentOut, summary='Сохранить вопросы и ответы')
async def save_content(test_id: int, body: ContentIn, db: Db, user: AdminUser) -> ContentOut:
    test = await _test(db, test_id)
    await service.save_content(db, test, body)
    record(db, 'test.content', 'test', test.id, user.id)
    await db.commit()
    return await service.content(db, test)


@router.post('/{test_id}/scales', response_model=ScaleOut, status_code=201, summary='Создать шкалу')
async def create_scale(test_id: int, body: ScaleIn, db: Db, user: AdminUser) -> ScaleOut:
    await _test(db, test_id)
    scale = await service.create_scale(db, body)
    record(db, 'scale.create', 'scale', scale.id, user.id)
    await db.commit()
    return service.scale_out(scale, 'full')


@router.put('/{test_id}/scales/{scale_id}', response_model=ScaleOut, summary='Изменить шкалу')
async def save_scale(test_id: int, scale_id: int, body: ScaleIn, db: Db, user: AdminUser) -> ScaleOut:
    test = await _test(db, test_id)
    scale = await db.get(Scale, scale_id)
    if scale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Шкала не найдена')
    mode = await service.save_scale(db, test, scale, body)
    record(db, 'scale.update', 'scale', scale.id, user.id)
    await db.commit()
    return service.scale_out(scale, mode)


@router.delete('/{test_id}', status_code=204, summary='Удалить методику, которую не выдавали')
async def delete_test(test_id: int, db: Db, user: AdminUser) -> None:
    test = await _test(db, test_id)
    if await service.assignments_count(db, test.id):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Методику уже выдавали классам: её можно только отключить')
    record(db, 'test.delete', 'test', test.id, user.id)
    await db.delete(test)
    await db.commit()


@router.get('/{test_id}/export', summary='Методика файлом JSON')
async def export_test(test_id: int, db: Db, _: AdminUser) -> dict:
    return service.export_test(await _test(db, test_id))


@router.get('/{test_id}/sample-input', summary='Пример входных данных расчёта')
async def sample_input(
    test_id: int, db: Db, _: AdminUser, mode: Literal['random', 'first', 'last'] = Query(default='random')
) -> dict:
    return service.sample_input(await _test(db, test_id), mode)


@router.put('/{test_id}/script', response_model=TestAdminDetail, summary='Сохранить скрипт расчёта')
async def save_script(test_id: int, body: ScriptIn, db: Db, user: AdminUser) -> TestAdminDetail:
    test = await _test(db, test_id)
    script = (body.script or '').strip() or None
    test.scoring_script = script
    record(db, 'test.script', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, test)


def _run_out(run: ScriptRun) -> RunOut:
    return RunOut(
        output=run.output,
        error=run.error,
        line=run.line,
        logs=run.logs,
        duration_ms=run.duration_ms,
        summary=summary(run.output),
    )


@router.post('/{test_id}/run', response_model=RunOut, summary='Проверить расчёт на данных, ничего не сохраняя')
async def run_script(test_id: int, body: RunIn, db: Db, _: AdminUser) -> RunOut:
    await _test(db, test_id)
    return _run_out(await service.run_script(body.script, body.input))


@router.get('/{test_id}/readiness', response_model=ReadinessOut, summary='Что мешает включить методику')
async def readiness(test_id: int, db: Db, _: AdminUser) -> ReadinessOut:
    problems = await service.readiness(await _test(db, test_id))
    return ReadinessOut(ready=not any(p.level == 'error' for p in problems), problems=problems)


@router.get('/{test_id}/preview', response_model=PreviewOut, summary='Методика глазами ученика')
async def preview(test_id: int, db: Db, _: AdminUser) -> PreviewOut:
    test = await _test(db, test_id)
    return PreviewOut(
        test=TestOut.model_validate(test),
        needs_birth_date=needs_birth_date(test),
        questions=[question_out(q) for q in sorted(test.questions, key=lambda q: q.order) if q.is_active],
    )


@router.post('/{test_id}/preview/result', response_model=RunOut, summary='Результат предпросмотра, ничего не сохраняя')
async def preview_result(test_id: int, body: PreviewResultIn, db: Db, _: AdminUser) -> RunOut:
    return _run_out(await service.preview_result(await _test(db, test_id), body))
