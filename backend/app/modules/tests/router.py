"""Администратор: методики, импорт из JSON, скрипт расчёта и его проверка."""

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sk_common.audit import record
from sk_common.deps import AdminUser, Db
from sqlalchemy import select

from app import scoring
from app.modules.assignments.service import summary
from app.modules.tests import service
from app.modules.tests.models import Test
from app.modules.tests.schemas import (
    ImportIn,
    RunIn,
    RunOut,
    ScriptIn,
    TestAdminBrief,
    TestAdminDetail,
    TestPatch,
)
from app.scoring import sandbox

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
        needs_birth_date=test.needs_birth_date or test.code in scoring.NEEDS_BIRTH_DATE,
        scoring_script=test.scoring_script,
    )


@router.get('', response_model=list[TestAdminBrief], summary='Все методики')
async def list_tests(db: Db, _: AdminUser) -> list[TestAdminBrief]:
    tests = await db.scalars(select(Test).order_by(Test.title))
    return [TestAdminBrief(**await _brief_fields(db, t)) for t in tests]


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
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(test, key, value)
    record(db, 'test.update', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, test)


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
    service.check_script_allowed(test.code, script)
    test.scoring_script = script
    record(db, 'test.script', 'test', test.id, user.id)
    await db.commit()
    return await _detail(db, test)


@router.post('/{test_id}/run', response_model=RunOut, summary='Проверить расчёт на данных, ничего не сохраняя')
async def run_script(test_id: int, body: RunIn, db: Db, _: AdminUser) -> RunOut:
    test = await _test(db, test_id)
    script = (body.script or '').strip()
    if script:
        run = await asyncio.to_thread(sandbox.run_script, script, body.input)
    else:
        run = sandbox.ScriptRun()
        try:
            run.output = scoring.calculate(test.code, body.input)
        except scoring.ScoringError as exc:
            run.error = str(exc)
        except Exception as exc:  # входные данные правят вручную: расчёт может упасть на любой их форме
            run.error = f'{type(exc).__name__}: {exc}'
    return RunOut(
        output=run.output,
        error=run.error,
        line=run.line,
        logs=run.logs,
        duration_ms=run.duration_ms,
        summary=summary(run.output),
    )
