"""Маршруты API v1."""

from fastapi import APIRouter

from .public import router as public_router


router = APIRouter()
router.include_router(public_router, prefix="/public", tags=["Public Attempts"])
