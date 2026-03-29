from fastapi import APIRouter

from .attempts import router as attempts_router


router = APIRouter()
router.include_router(attempts_router, prefix="/attempts")
