"""
Бизнес-логика публичного прохождения диагностики.

Обслуживает анонимные попытки по токену: получение бандла данных,
старт, сохранение ответов и отправку попытки.
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from src.core.logging import get_logger
from src.core.nocobase import nocobase_client
from src.schemas.public import AnswerUpdatePayload

logger = get_logger(__name__)

# Статусы, означающие завершённую попытку
FINISHED_STATUSES = {'submitted', 'completed'}


def normalize_id(value: Any) -> Any:
    """Привести значение ID к int, если это числовая строка."""
    if value in (None, ''):
        return value
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text) if text.isdigit() else value


def now_iso() -> str:
    """Текущее время UTC в формате ISO 8601 с суффиксом Z."""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def calculate_duration(started_at: str | None, fallback: Any = None) -> int | Any:
    """Вычислить продолжительность в секундах от *started_at* до текущего момента."""
    if not started_at:
        return fallback
    started_ts = datetime.fromisoformat(started_at.replace('Z', '+00:00')).timestamp()
    return max(0, round(datetime.now(timezone.utc).timestamp() - started_ts))


class PublicAttemptsService:
    """Сервис публичного прохождения тестов по анонимной ссылке (token)."""

    async def get_attempt_by_token(self, token: str) -> dict[str, Any]:
        """Найти активную попытку по токену или вернуть 404."""
        logger.info("Поиск попытки по токену: %s", token[:8] + '...')
        attempts = await nocobase_client.list(
            'attempts',
            filter={'token': token},
            appends='test_assignment,test_assignment.test,person',
            page_size=1,
        )
        if not attempts:
            logger.warning("Попытка не найдена: token=%s", token[:8] + '...')
            raise HTTPException(status_code=404, detail='Attempt not found')
        return attempts[0]

    async def get_or_create_answer(self, attempt_id: Any, question_id: Any) -> dict[str, Any]:
        """Найти ответ по ID попытки и вопроса, создать если не существует."""
        answers = await nocobase_client.list(
            'answers',
            filter={
                'attempt_id': normalize_id(attempt_id),
                'question_id': normalize_id(question_id),
            },
            appends='option,scale_option,options,question',
            page_size=1,
        )
        if answers:
            return answers[0]

        logger.warning(
            "[get_or_create_answer] Ответ не найден, создаём: attempt=%s question=%s",
            attempt_id, question_id,
        )
        new_answer = await nocobase_client.create(
            'answers',
            {
                'attempt': normalize_id(attempt_id),
                'question': normalize_id(question_id),
            },
        )
        answers = await nocobase_client.list(
            'answers',
            filter={'id': normalize_id(new_answer['id'])},
            appends='option,scale_option,options,question',
            page_size=1,
        )
        if not answers:
            raise HTTPException(status_code=500, detail='Failed to create answer')
        return answers[0]

    async def list_ranking_items(self, answer_id: Any) -> list[dict[str, Any]]:
        """Получить элементы ранжирования для ответа."""
        return await nocobase_client.list(
            'answer_ranking_items',
            filter={'answer_id': normalize_id(answer_id)},
            appends='option',
            sort='rank,id',
        )

    async def build_bundle(self, attempt: dict[str, Any]) -> dict[str, Any]:
        """Собрать полный бандл данных для прохождения: вопросы, ответы, варианты, шкалы."""
        ta = attempt.get('test_assignment') or {}
        test_id = ta.get('test_id') or (ta.get('test') or {}).get('id')
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
        """Основной эндпоинт: получить попытку + бандл по токену."""
        logger.info("Запрос бандла: token=%s", token[:8] + '...')
        attempt = await self.get_attempt_by_token(token)
        return await self.build_bundle(attempt)

    async def start_attempt(self, token: str) -> dict[str, Any]:
        """Начать попытку: перевести из 'assigned' в 'in_progress'."""
        logger.info("Старт попытки: token=%s", token[:8] + '...')
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
        """Отправить попытку: зафиксировать время завершения и продолжительность."""
        logger.info("Отправка попытки: token=%s", token[:8] + '...')
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
        """
        Синхронизировать элементы ранжирования: удалить лишние,
        обновить существующие, создать новые.
        """
        t0 = time.perf_counter()

        existing_items = await nocobase_client.list(
            'answer_ranking_items',
            filter={'answer_id': normalize_id(answer_id)},
            sort='rank,id',
        )
        t1 = time.perf_counter()
        logger.info(
            "[sync_ranking] answer_id=%s  list existing: %d items  %.0f ms",
            answer_id, len(existing_items), (t1 - t0) * 1000,
        )

        existing_by_option_id = {
            normalize_id(item['option_id']): item
            for item in existing_items
        }
        next_option_ids = [normalize_id(value) for value in ranked_option_ids]

        # ── Удаление лишних ──────────────────────────────────────────────
        to_delete = [
            item for item in existing_items
            if normalize_id(item['option_id']) not in next_option_ids
        ]
        for item in to_delete:
            t_del = time.perf_counter()
            await nocobase_client.destroy('answer_ranking_items', item['id'])
            logger.info(
                "[sync_ranking]   destroy id=%s  %.0f ms",
                item['id'], (time.perf_counter() - t_del) * 1000,
            )

        # ── Upsert ───────────────────────────────────────────────────────
        for index, option_id in enumerate(next_option_ids, start=1):
            payload = {
                'answer_id': normalize_id(answer_id),
                'option_id': option_id,
                'rank': index,
            }
            existing = existing_by_option_id.get(option_id)
            t_up = time.perf_counter()
            if existing:
                await nocobase_client.update('answer_ranking_items', existing['id'], payload)
                logger.info(
                    "[sync_ranking]   update id=%s rank=%d  %.0f ms",
                    existing['id'], index, (time.perf_counter() - t_up) * 1000,
                )
            else:
                await nocobase_client.create('answer_ranking_items', payload)
                logger.info(
                    "[sync_ranking]   create option=%s rank=%d  %.0f ms",
                    option_id, index, (time.perf_counter() - t_up) * 1000,
                )

        # ── Финальная выборка ─────────────────────────────────────────────
        t_final = time.perf_counter()
        result = await self.list_ranking_items(answer_id)
        logger.info(
            "[sync_ranking]   final list: %d items  %.0f ms  │  TOTAL %.0f ms",
            len(result), (time.perf_counter() - t_final) * 1000,
            (time.perf_counter() - t0) * 1000,
        )
        return result

    def validate_attempt_for_update(self, attempt: dict[str, Any]) -> None:
        """Проверить, что попытка находится в состоянии, допускающем редактирование ответов."""
        if attempt.get('status') == 'assigned':
            raise HTTPException(status_code=409, detail='Attempt has not started')
        if attempt.get('status') in FINISHED_STATUSES:
            raise HTTPException(status_code=409, detail='Attempt already finished')

    async def update_answer_for_attempt(
        self,
        attempt: dict[str, Any],
        question_id: Any,
        payload: AnswerUpdatePayload,
    ) -> dict[str, Any]:
        """Обновить ответ с проверкой состояния попытки и обработкой ranking/options."""
        t0 = time.perf_counter()
        self.validate_attempt_for_update(attempt)

        t1 = time.perf_counter()
        answer = await self.get_or_create_answer(attempt['id'], question_id)
        logger.info("[update_answer] get_or_create_answer  %.0f ms", (time.perf_counter() - t1) * 1000)

        data = payload.model_dump(exclude_unset=True)
        ranking_payload = data.pop('ranking', None)
        options_payload = data.pop('options', None)
        ranking_items: list[dict[str, Any]] | None = None

        if options_payload is not None:
            t_opt = time.perf_counter()
            await nocobase_client.set_relation(
                'answers',
                answer['id'],
                'options',
                [normalize_id(value) for value in options_payload],
            )
            logger.info("[update_answer] set_relation options  %.0f ms", (time.perf_counter() - t_opt) * 1000)
            data.setdefault('option_id', None)
            data.setdefault('scale_option_id', None)
            data.setdefault('text', None)
            data.setdefault('number', None)
            data.setdefault('boolean', None)
            data['is_skipped'] = False

        if ranking_payload is not None:
            t_rank = time.perf_counter()
            ranking_items = await self.sync_ranking(answer['id'], ranking_payload)
            logger.info("[update_answer] sync_ranking  %.0f ms", (time.perf_counter() - t_rank) * 1000)
            data['is_skipped'] = False

        if data:
            t_upd = time.perf_counter()
            await nocobase_client.update('answers', answer['id'], data)
            logger.info("[update_answer] update answer fields  %.0f ms", (time.perf_counter() - t_upd) * 1000)

        t_get = time.perf_counter()
        updated_answer = await nocobase_client.get(
            'answers',
            answer['id'],
            appends='option,scale_option,options,question',
        )
        logger.info("[update_answer] get updated answer  %.0f ms", (time.perf_counter() - t_get) * 1000)

        if ranking_payload is not None and ranking_items is None:
            t_ri = time.perf_counter()
            ranking_items = await self.list_ranking_items(answer['id'])
            logger.info("[update_answer] list_ranking_items  %.0f ms", (time.perf_counter() - t_ri) * 1000)

        logger.info("[update_answer] TOTAL  %.0f ms", (time.perf_counter() - t0) * 1000)
        if ranking_items is None:
            return {'answer': updated_answer}
        return {'answer': updated_answer, 'ranking_items': ranking_items}

    async def update_answer(self, token: str, question_id: Any, payload: AnswerUpdatePayload) -> dict[str, Any]:
        """Публичный эндпоинт обновления ответа по токену и ID вопроса."""
        logger.info("Обновление ответа: token=%s question=%s", token[:8] + '...', question_id)
        attempt = await self.get_attempt_by_token(token)
        return await self.update_answer_for_attempt(attempt, question_id, payload)

    async def get_test_assignment_by_public_token(self, public_token: str) -> dict[str, Any]:
        """Найти test_assignment по публичному токену или вернуть 404."""
        logger.info("Поиск test_assignment по public_token: %s", public_token[:8] + '...')
        assignments = await nocobase_client.list(
            'test_assignments',
            filter={'public_token': public_token, 'is_active': True},
            appends='test',
            page_size=1,
        )
        if not assignments:
            logger.warning("test_assignment не найдена: public_token=%s", public_token[:8] + '...')
            raise HTTPException(status_code=404, detail='Test not found')
        return assignments[0]

    async def get_test_info(self, public_token: str) -> dict[str, Any]:
        """Получить информацию о тесте по публичному токену (для интро экрана)."""
        logger.info("Запрос информации о тесте: public_token=%s", public_token[:8] + '...')
        test_assignment = await self.get_test_assignment_by_public_token(public_token)
        test = test_assignment.get('test') or {}
        return {
            'test_assignment': test_assignment,
            'test': test,
        }

    async def start_test(self, public_token: str) -> dict[str, Any]:
        """Начать прохождение: создать новую попытку с генерированным токеном."""
        logger.info("Начало теста: public_token=%s", public_token[:8] + '...')
        test_assignment = await self.get_test_assignment_by_public_token(public_token)

        # Генерируем уникальный токен для анонимной попытки
        attempt_token = secrets.token_urlsafe(16)
        logger.info("Созданный токен для попытки: %s", attempt_token[:8] + '...')

        # Создаём новую попытку
        attempt = await nocobase_client.create(
            'attempts',
            {
                'test_assignment': test_assignment['id'],
                'token': attempt_token,
                'status': 'assigned',
            },
        )
        logger.info("Попытка создана с ID: %s", attempt['id'])

        # Получаем созданную попытку со всеми аппендами
        attempt = await self.get_attempt_by_token(attempt_token)

        # Возвращаем полный бандл
        # Пустые ответы создаёт NocoBase workflow при создании попытки
        return await self.build_bundle(attempt)

public_attempts_service = PublicAttemptsService()
