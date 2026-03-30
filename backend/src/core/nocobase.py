"""
HTTP-клиент для взаимодействия с NocoBase REST API.

Предоставляет CRUD-операции над коллекциями: list, get, create, update,
destroy, set_relation.  Каждый вызов открывает отдельный ``httpx.AsyncClient``
(stateless), что упрощает конфигурацию и потокобезопасность.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# Максимальное количество записей, запрашиваемых за один раз
DEFAULT_PAGE_SIZE = 500


class NocoBaseClient:
    """Асинхронный клиент к NocoBase API."""

    def _normalize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Привести параметры запроса к плоскому строковому виду."""
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                normalized[key] = ','.join(str(item) for item in value)
            else:
                normalized[key] = value
        return normalized

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_payload: Any = None,
    ) -> httpx.Response:
        """Выполнить HTTP-запрос к NocoBase и вернуть ответ."""
        if not settings.api_key:
            raise HTTPException(status_code=500, detail='API_KEY is not configured')

        headers = {
            'Authorization': f'Bearer {settings.api_key}',
            'Content-Type': 'application/json',
        }

        logger.debug("NocoBase → %s %s  params=%s", method, path, params)

        async with httpx.AsyncClient(
            base_url=settings.nocobase_api_url,
            timeout=settings.nocobase_timeout,
            headers=headers,
        ) as client:
            response = await client.request(
                method,
                path,
                params=self._normalize_params(params or {}),
                json=json_payload,
            )

        if response.status_code >= 400:
            detail: Any = response.text
            try:
                detail = response.json()
            except Exception:
                pass
            logger.warning("NocoBase ← %s %s  status=%d", method, path, response.status_code)
            raise HTTPException(status_code=response.status_code, detail=detail)

        logger.debug("NocoBase ← %s %s  status=%d", method, path, response.status_code)
        return response

    async def list(
        self,
        collection: str,
        *,
        filter: dict[str, Any] | None = None,
        appends: str | list[str] | None = None,
        sort: str | list[str] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        """Получить список записей коллекции с фильтрацией и сортировкой."""
        response = await self._request(
            'GET',
            f'/{collection}:list',
            params={
                'pageSize': page_size,
                'filter': json.dumps(filter) if filter is not None else None,
                'appends': appends,
                'sort': sort,
            },
        )
        payload = response.json()
        return payload.get('data') or []

    async def get(
        self,
        collection: str,
        filter_by_tk: str | int,
        *,
        appends: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Получить одну запись коллекции по первичному ключу."""
        response = await self._request(
            'GET',
            f'/{collection}:get',
            params={'filterByTk': filter_by_tk, 'appends': appends},
        )
        return response.json().get('data') or {}

    async def create(self, collection: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Создать запись в коллекции."""
        response = await self._request('POST', f'/{collection}:create', json_payload=payload)
        return response.json().get('data') or {}

    async def update(self, collection: str, record_id: str | int, payload: dict[str, Any]) -> dict[str, Any]:
        """Обновить запись коллекции по ID."""
        response = await self._request(
            'POST',
            f'/{collection}:update',
            params={'filterByTk': record_id},
            json_payload=payload,
        )
        return response.json().get('data') or {}

    async def destroy(self, collection: str, record_id: str | int) -> None:
        """Удалить запись из коллекции (пробует DELETE, при ошибке — POST)."""
        try:
            await self._request('DELETE', f'/{collection}:destroy', params={'filterByTk': record_id})
        except HTTPException:
            await self._request('POST', f'/{collection}:destroy', params={'filterByTk': record_id})

    async def set_relation(self, collection: str, record_id: str | int, relation: str, ids: list[str | int]) -> Any:
        """Установить связь many-to-many, пробуя несколько стратегий NocoBase API."""
        strategies = [
            lambda: self.update(collection, record_id, {relation: ids}),
            lambda: self.update(collection, record_id, {relation: [{'id': value} for value in ids]}),
            lambda: self._request('POST', f'/{collection}/{record_id}/{relation}:set', json_payload={'values': ids}),
            lambda: self._request('POST', f'/{collection}/{record_id}/{relation}:set', json_payload=ids),
        ]

        last_error: HTTPException | None = None
        for strategy in strategies:
            try:
                return await strategy()
            except HTTPException as error:
                last_error = error

        if last_error:
            raise last_error
        raise HTTPException(status_code=500, detail='Failed to update relation')


nocobase_client = NocoBaseClient()
