"""Маршруты API v1."""

from fastapi import APIRouter

from .public.attempts import router as public_attempts_router
from .public.tests import router as public_tests_router


router = APIRouter()
router.include_router(public_tests_router, prefix="/public/tests", tags=["Public Tests"])
router.include_router(public_attempts_router, prefix="/public/attempts", tags=["Public Attempts"])
