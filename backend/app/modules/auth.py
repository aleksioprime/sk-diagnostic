"""Вход — из sk_common. В ответе /me — относится ли человек к психологической службе."""

from fastapi import Request
from sk_common.auth.router import create_auth_router
from sk_common.auth.schemas import Me
from sk_common.people.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.staff.permissions import is_psychologist


class DiagnosticMe(Me):
    is_psychologist: bool = False


async def _me_extra(db: AsyncSession, request: Request, user: User) -> dict:
    return {'is_psychologist': await is_psychologist(db, user)}


router = create_auth_router(me_model=DiagnosticMe, me_extra=_me_extra)
