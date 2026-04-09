"""
Маршруты публичного API для инициирования прохождения тестов по публичному токену.

Эндпоинты доступны без авторизации — достаточно знать публичный токен теста.
"""

from fastapi import APIRouter

from src.services.public_attempts import public_attempts_service


router = APIRouter()


@router.get('/{public_token}')
async def get_test_info(public_token: str):
    """Получить информацию о тесте по публичному токену (для интро экрана)."""
    return await public_attempts_service.get_test_info(public_token)


@router.post('/{public_token}/start')
async def start_test(public_token: str):
    """Начать прохождение: создать новую попытку и вернуть её данные с токеном."""
    return await public_attempts_service.start_test(public_token)
