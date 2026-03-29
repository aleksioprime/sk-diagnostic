from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from src.core.nocobase import nocobase_client
from src.schemas.public import AnswerUpdatePayload


FINISHED_STATUSES = {'submitted', 'completed'}


def normalize_id(value: Any) -> Any:
    if value in (None, ''):
        return value
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text) if text.isdigit() else value


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def calculate_duration(started_at: str | None, fallback: Any = None) -> int | Any:
    if not started_at:
        return fallback
    started_ts = datetime.fromisoformat(started_at.replace('Z', '+00:00')).timestamp()
    return max(0, round(datetime.now(timezone.utc).timestamp() - started_ts))


class PublicAttemptsService:
    async def get_attempt_by_token(self, token: str) -> dict[str, Any]:
        attempts = await nocobase_client.list(
            'attempts',
            filter={'token': token, 'is_archived': {'$ne': True}},
            appends='test,person',
            page_size=1,
        )
        if not attempts:
            raise HTTPException(status_code=404, detail='Attempt not found')
        return attempts[0]

    async def get_answer(self, attempt_id: Any, question_id: Any) -> dict[str, Any]:
        answers = await nocobase_client.list(
            'answers',
            filter={
                'attempt_id': normalize_id(attempt_id),
                'question_id': normalize_id(question_id),
            },
            appends='option,scale_option,options,question',
            page_size=1,
        )
        if not answers:
            raise HTTPException(status_code=404, detail='Answer not found')
        return answers[0]

    async def list_ranking_items(self, answer_id: Any) -> list[dict[str, Any]]:
        return await nocobase_client.list(
            'answer_ranking_items',
            filter={'answer_id': normalize_id(answer_id)},
            appends='option',
            sort='rank,id',
        )

    async def build_bundle(self, attempt: dict[str, Any]) -> dict[str, Any]:
        if attempt.get('is_archived'):
            raise HTTPException(status_code=404, detail='Attempt is archived')

        test_id = attempt.get('test_id') or attempt.get('test', {}).get('id')
        if not test_id:
            raise HTTPException(status_code=400, detail='Attempt has no test')

        questions = await nocobase_client.list(
            'questions',
            filter={'test_id': normalize_id(test_id), 'is_active': True},
            sort='order,id',
        )
        answers = await nocobase_client.list(
            'answers',
            filter={'attempt_id': normalize_id(attempt['id'])},
            appends='option,scale_option,options,question',
            sort='id',
        )

        question_ids = [question['id'] for question in questions]
        scale_ids = sorted({
            normalize_id(question.get('scale_id'))
            for question in questions
            if question.get('scale_id') is not None
        })
        answer_ids = [answer['id'] for answer in answers]

        options = []
        scales = []
        scale_options = []
        ranking_items = []

        if question_ids:
            options = await nocobase_client.list(
                'options',
                filter={'question_id': {'$in': question_ids}, 'is_active': True},
                sort='order,id',
            )
        if scale_ids:
            scales = await nocobase_client.list(
                'scales',
                filter={'id': {'$in': scale_ids}, 'is_active': True},
                sort='id',
            )
            scale_options = await nocobase_client.list(
                'scale_options',
                filter={'scale_id': {'$in': scale_ids}, 'is_active': True},
                sort='order,id',
            )
        if answer_ids:
            ranking_items = await nocobase_client.list(
                'answer_ranking_items',
                filter={'answer_id': {'$in': answer_ids}},
                appends='option',
                sort='rank,id',
            )

        return {
            'attempt': attempt,
            'questions': questions,
            'answers': answers,
            'options': options,
            'scales': scales,
            'scale_options': scale_options,
            'ranking_items': ranking_items,
        }

    async def get_bundle(self, token: str) -> dict[str, Any]:
        attempt = await self.get_attempt_by_token(token)
        return await self.build_bundle(attempt)

    async def start_attempt(self, token: str) -> dict[str, Any]:
        attempt = await self.get_attempt_by_token(token)
        if attempt.get('status') == 'assigned':
            await nocobase_client.update(
                'attempts',
                attempt['id'],
                {'status': 'in_progress', 'started_at': now_iso()},
            )
            attempt = await self.get_attempt_by_token(token)
        return await self.build_bundle(attempt)

    async def submit_attempt(self, token: str) -> dict[str, Any]:
        attempt = await self.get_attempt_by_token(token)
        if attempt.get('status') in FINISHED_STATUSES:
            return {'attempt': attempt}

        updated_attempt = await nocobase_client.update(
            'attempts',
            attempt['id'],
            {
                'status': 'submitted',
                'submitted_at': now_iso(),
                'duration': calculate_duration(attempt.get('started_at'), attempt.get('duration')),
            },
        )
        return {'attempt': updated_attempt or await self.get_attempt_by_token(token)}

    async def sync_ranking(self, answer_id: Any, ranked_option_ids: list[Any]) -> list[dict[str, Any]]:
        existing_items = await nocobase_client.list(
            'answer_ranking_items',
            filter={'answer_id': normalize_id(answer_id)},
            sort='rank,id',
        )
        existing_by_option_id = {
            normalize_id(item['option_id']): item
            for item in existing_items
        }
        next_option_ids = [normalize_id(value) for value in ranked_option_ids]

        for item in existing_items:
            if normalize_id(item['option_id']) not in next_option_ids:
                await nocobase_client.destroy('answer_ranking_items', item['id'])

        for index, option_id in enumerate(next_option_ids, start=1):
            payload = {
                'answer_id': normalize_id(answer_id),
                'option_id': option_id,
                'rank': index,
            }
            existing = existing_by_option_id.get(option_id)
            if existing:
                await nocobase_client.update('answer_ranking_items', existing['id'], payload)
            else:
                await nocobase_client.create('answer_ranking_items', payload)

        return await self.list_ranking_items(answer_id)

    async def update_answer(self, token: str, question_id: Any, payload: AnswerUpdatePayload) -> dict[str, Any]:
        attempt = await self.get_attempt_by_token(token)
        if attempt.get('status') == 'assigned':
            raise HTTPException(status_code=409, detail='Attempt has not started')
        if attempt.get('status') in FINISHED_STATUSES:
            raise HTTPException(status_code=409, detail='Attempt already finished')

        answer = await self.get_answer(attempt['id'], question_id)
        data = payload.model_dump(exclude_unset=True)
        ranking_payload = data.pop('ranking', None)
        options_payload = data.pop('options', None)
        ranking_items: list[dict[str, Any]] = []

        if options_payload is not None:
            await nocobase_client.set_relation(
                'answers',
                answer['id'],
                'options',
                [normalize_id(value) for value in options_payload],
            )
            data.setdefault('option_id', None)
            data.setdefault('scale_option_id', None)
            data.setdefault('text', None)
            data.setdefault('number', None)
            data.setdefault('boolean', None)
            data['is_skipped'] = False

        if ranking_payload is not None:
            ranking_items = await self.sync_ranking(answer['id'], ranking_payload)
            data['is_skipped'] = False

        if data:
            await nocobase_client.update('answers', answer['id'], data)

        updated_answer = await nocobase_client.get(
            'answers',
            answer['id'],
            appends='option,scale_option,options,question',
        )
        if not ranking_items:
            ranking_items = await self.list_ranking_items(answer['id'])

        return {'answer': updated_answer, 'ranking_items': ranking_items}


public_attempts_service = PublicAttemptsService()
