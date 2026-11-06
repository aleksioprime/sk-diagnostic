"""
Перенос диагностик из NocoBase.

    python -m app.cli nocobase-fetch /data/nocobase   # API NocoBase → JSON-файлы (только чтение)
    python -m app.cli nocobase-load /data/nocobase    # JSON-файлы → база SK Diagnostic

Перед загрузкой синхронизируйте справочник SkolStream: ученики сопоставляются по UUID SkolStream.
ID записей сохраняются. Пустые ответы-заготовки NocoBase не переносятся. Результаты пересчитываются
заново; если новый расчёт не совпал с сохранённым в NocoBase, это попадает в report.json.
Повторная загрузка пропускает уже перенесённое.
"""

import json
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
from sk_common.people.models import PERSON_SOURCE_SKOLSTREAM, Person
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import scoring
from app.modules.attempts import service as attempts_service
from app.modules.attempts.models import (
    STATUS_ASSIGNED,
    STATUS_IN_PROGRESS,
    STATUS_SUBMITTED,
    Answer,
    Assignment,
    Attempt,
    RankingItem,
)
from app.modules.tests.models import QUESTION_TYPES, Option, Question, Scale, ScaleOption, Test

logger = logging.getLogger('sk_diagnostic.nocobase')

COLLECTIONS: dict[str, list[str]] = {
    'persons': [],
    'scales': [],
    'scale_options': [],
    'tests': [],
    'questions': [],
    'options': [],
    'test_assignments': [],
    'attempts': [],
    'answers': [],
    'answer_ranking_items': [],
    'attempt_results': [],
}

STATUSES = {'assigned': STATUS_ASSIGNED, 'in_progress': STATUS_IN_PROGRESS, 'submitted': STATUS_SUBMITTED}


async def fetch(base_url: str, api_key: str, target: Path, page_size: int = 500) -> dict[str, int]:
    """Все записи нужных коллекций постранично. Ничего не меняет в NocoBase."""
    target.mkdir(parents=True, exist_ok=True)
    counts = {}
    headers = {'Authorization': f'Bearer {api_key}', 'X-Role': 'root'}
    async with httpx.AsyncClient(base_url=base_url.rstrip('/'), headers=headers, timeout=60) as client:
        for name, appends in COLLECTIONS.items():
            rows: list[dict] = []
            page = 1
            while True:
                params: list[tuple[str, Any]] = [('page', page), ('pageSize', page_size), ('sort', 'id')]
                params += [('appends[]', a) for a in appends]
                response = await client.get(f'/api/{name}:list', params=params)
                response.raise_for_status()
                body = response.json()
                chunk = body.get('data') or []
                rows += chunk
                meta = body.get('meta') or {}
                if len(chunk) < page_size or page >= meta.get('totalPage', page):
                    break
                page += 1
            (target / f'{name}.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str))
            counts[name] = len(rows)
            logger.info('%s: %s записей', name, len(rows))
    return counts


def _read(source: Path, name: str) -> list[dict]:
    path = source / f'{name}.json'
    return json.loads(path.read_text()) if path.exists() else []


def _dt(value) -> datetime | None:
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')) if value else None


def _date(value) -> date | None:
    return date.fromisoformat(str(value)[:10]) if value else None


def _text(value, limit: int | None = None) -> str:
    text = (str(value) if value is not None else '').strip()
    return text[:limit] if limit else text


def _int(value) -> int | None:
    return int(value) if value not in (None, '') else None


def _float(value) -> float | None:
    return float(value) if value not in (None, '') else None


def _stamps(row: dict) -> dict:
    created = _dt(row.get('createdAt'))
    return {'created_at': created, 'updated_at': _dt(row.get('updatedAt')) or created} if created else {}


def _comparable(result: dict | None) -> dict | None:
    if not result:
        return None
    result = json.loads(json.dumps(result))
    result.get('result', {}).pop('calculated_at', None)
    # У ученика новый ID, а ФИО в NocoBase иногда было с отчеством — сравниваются только расчёты
    for key in ('id', 'name'):
        result.get('student', {}).pop(key, None)
    return result


class Loader:
    def __init__(self, session: AsyncSession, source: Path):
        self.session = session
        self.data = {name: _read(source, name) for name in COLLECTIONS}
        self.counts: dict[str, int] = {}
        self.skipped: dict[str, list] = {}
        self.result_changes: list[dict] = []
        self.persons: dict[int, int] = {}  # id персоны NocoBase → id персоны SK Diagnostic

    def skip(self, kind: str, nb_id, reason: str) -> None:
        self.skipped.setdefault(kind, []).append({'id': nb_id, 'reason': reason})

    def count(self, kind: str) -> None:
        self.counts[kind] = self.counts.get(kind, 0) + 1

    async def _exists(self, model, nb_id) -> bool:
        return await self.session.get(model, int(nb_id)) is not None

    async def _add(self, kind: str, model, row: dict, **fields) -> None:
        if await self._exists(model, row['id']):
            return
        self.session.add(model(id=int(row['id']), **fields, **_stamps(row)))
        self.count(kind)

    async def person(self, row: dict) -> int | None:
        """Ученик из справочника SkolStream; если его там нет — карточка с UUID, справочник её дополнит."""
        skolstream_id = row.get('skolstream_id')
        person = None
        if skolstream_id:
            person = await self.session.scalar(select(Person).where(Person.skolstream_id == uuid.UUID(skolstream_id)))
        if person is None:
            if not skolstream_id:
                self.skip('persons', row['id'], 'нет UUID SkolStream')
                return None
            person = Person(
                source=PERSON_SOURCE_SKOLSTREAM,
                skolstream_id=uuid.UUID(skolstream_id),
                last_name=_text(row.get('last_name'), 100),
                first_name=_text(row.get('first_name'), 100),
                middle_name=_text(row.get('middle_name'), 100),
                email=_text(row.get('email'), 255).lower() or None,
                is_student=True,
            )
            self.session.add(person)
            self.count('persons_created')
        # Дату рождения вводили в NocoBase; в SkolStream её нет
        if person.birth_date is None and row.get('birth_date'):
            person.birth_date = _date(row['birth_date'])
            self.count('birth_dates')
        if not person.gender and row.get('gender'):
            person.gender = row['gender']
        await self.session.flush()
        return person.id

    async def run(self) -> dict:
        for row in self.data['scales']:
            await self._add(
                'scales',
                Scale,
                row,
                title=_text(row.get('title'), 255),
                code=_text(row.get('code'), 100) or None,
                description=_text(row.get('description')),
                is_active=row.get('is_active') is not False,
            )
        await self.session.flush()
        for row in self.data['scale_options']:
            await self._add(
                'scale_options',
                ScaleOption,
                row,
                scale_id=int(row['scale_id']),
                label=_text(row.get('label'), 255),
                description=_text(row.get('description')),
                value=_text(row.get('value'), 100),
                score=_float(row.get('score')),
                order=_int(row.get('order')) or 0,
                is_active=row.get('is_active') is not False,
            )
        for row in self.data['tests']:
            await self._add(
                'tests',
                Test,
                row,
                title=_text(row.get('title'), 500),
                code=_text(row.get('code'), 100),
                description=_text(row.get('description')),
                is_sequential=row.get('is_sequential') is not False,
                needs_birth_date=row.get('code') == 'motivation_learning',
                scoring_script=scoring.nocobase_script(_text(row.get('code'), 100)),
            )
        await self.session.flush()
        for row in self.data['questions']:
            if row.get('question_type') not in QUESTION_TYPES:
                self.skip('questions', row['id'], f'неизвестный тип {row.get("question_type")}')
                continue
            await self._add(
                'questions',
                Question,
                row,
                test_id=int(row['test_id']),
                order=_int(row.get('order')) or 0,
                code=_text(row.get('code'), 100) or None,
                text=_text(row.get('text')) or '—',
                description=_text(row.get('description')),
                question_type=row['question_type'],
                is_required=row.get('is_required') is not False,
                is_active=row.get('is_active') is not False,
                is_random=bool(row.get('random')),
                min_selections=_int(row.get('min_selections')),
                max_selections=_int(row.get('max_selections')),
                scale_id=_int(row.get('scale_id')),
            )
        await self.session.flush()
        for row in self.data['options']:
            await self._add(
                'options',
                Option,
                row,
                question_id=int(row['question_id']),
                label=_text(row.get('label'), 500),
                description=_text(row.get('description')),
                value=_text(row.get('value'), 100),
                score=_float(row.get('score')),
                order=_int(row.get('order')) or 0,
                is_active=row.get('is_active') is not False,
            )
        for row in self.data['test_assignments']:
            await self._add(
                'assignments',
                Assignment,
                row,
                test_id=int(row['test_id']),
                title=_text(row.get('title'), 500) or 'Выдача',
                public_token=_text(row.get('public_token'), 64) or None,
                is_active=bool(row.get('is_active')),
            )
        await self.session.flush()

        nb_persons = {int(p['id']): p for p in self.data['persons']}
        for row in self.data['attempts']:
            if await self._exists(Attempt, row['id']):
                continue
            nb_person = _int(row.get('person_id'))
            if nb_person not in self.persons:
                if nb_person not in nb_persons:
                    self.skip('attempts', row['id'], 'нет ученика')
                    continue
                self.persons[nb_person] = await self.person(nb_persons[nb_person])
            if self.persons[nb_person] is None:
                self.skip('attempts', row['id'], 'ученик не сопоставлен со SkolStream')
                continue
            await self._add(
                'attempts',
                Attempt,
                row,
                assignment_id=int(row['test_assignment_id']),
                person_id=self.persons[nb_person],
                status=STATUSES.get(row.get('status'), STATUS_ASSIGNED),
                started_at=_dt(row.get('started_at')),
                submitted_at=_dt(row.get('submitted_at')),
                duration=_int(row.get('duration')),
            )
        await self.session.flush()

        attempts = set(await self.session.scalars(select(Attempt.id)))
        ranked = {int(r['answer_id']) for r in self.data['answer_ranking_items']}
        for row in self.data['answers']:
            empty = all(row.get(k) is None for k in ('option_id', 'scale_option_id', 'text', 'number', 'boolean'))
            if empty and int(row['id']) not in ranked:
                continue  # заготовка ответа, которую NocoBase создавал заранее
            if int(row['attempt_id']) not in attempts:
                self.skip('answers', row['id'], 'нет попытки')
                continue
            await self._add(
                'answers',
                Answer,
                row,
                attempt_id=int(row['attempt_id']),
                question_id=int(row['question_id']),
                option_id=_int(row.get('option_id')),
                scale_option_id=_int(row.get('scale_option_id')),
                text=row.get('text'),
                number=_float(row.get('number')),
                boolean=row.get('boolean'),
            )
        await self.session.flush()
        answers = set(await self.session.scalars(select(Answer.id)))
        for row in self.data['answer_ranking_items']:
            if int(row['answer_id']) not in answers:
                self.skip('ranking', row['id'], 'нет ответа')
                continue
            await self._add(
                'ranking_items',
                RankingItem,
                row,
                answer_id=int(row['answer_id']),
                option_id=int(row['option_id']),
                rank=_int(row.get('rank')) or 0,
            )
        await self.session.flush()
        await self.recalculate()
        return {'counts': self.counts, 'skipped': self.skipped, 'result_changes': self.result_changes}

    async def recalculate(self) -> None:
        """Результаты завершённых попыток считаются заново и сверяются с сохранёнными в NocoBase."""
        saved = {}
        for row in self.data['attempt_results']:
            data = row.get('json_results') or {}
            saved[int(row['attempt_id'])] = data.get('json', data)
        rows = await self.session.scalars(select(Attempt).where(Attempt.status == STATUS_SUBMITTED))
        for attempt in rows.unique():
            await self.session.refresh(attempt, ['result'])
            if attempt.result is not None:
                continue
            result = await attempts_service.calculate(self.session, attempt)
            self.count('results' if result.error is None else 'results_failed')
            before = _comparable(saved.get(attempt.id))
            after = _comparable(result.data)
            if before is not None and before != after:
                self.result_changes.append({'attempt_id': attempt.id, 'error': result.error})


async def load(session: AsyncSession, source: Path) -> dict:
    report = await Loader(session, source).run()
    (source / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return report
