from fastapi import APIRouter

from src.schemas.public import AnswerUpdatePayload
from src.services.public_attempts import public_attempts_service


router = APIRouter()


@router.get('/{token}')
async def get_attempt_bundle(token: str):
    return await public_attempts_service.get_bundle(token)


@router.post('/{token}/start')
async def start_attempt(token: str):
    return await public_attempts_service.start_attempt(token)


@router.patch('/{token}/answers/{question_id}')
async def update_answer(token: str, question_id: str, payload: AnswerUpdatePayload):
    return await public_attempts_service.update_answer(token, question_id, payload)


@router.post('/{token}/submit')
async def submit_attempt(token: str):
    return await public_attempts_service.submit_attempt(token)
