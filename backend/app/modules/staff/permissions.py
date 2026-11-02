from typing import Annotated

from fastapi import Depends, HTTPException, status
from sk_common.deps import CurrentUser, Db
from sk_common.people.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.staff.models import Psychologist


async def is_psychologist(db: AsyncSession, user: User) -> bool:
    if user.is_superuser:
        return True
    return bool(await db.scalar(select(Psychologist.user_id).where(Psychologist.user_id == user.id)))


async def require_psychologist(db: Db, user: CurrentUser) -> User:
    if not await is_psychologist(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Раздел для психологической службы')
    return user


PsychologistUser = Annotated[User, Depends(require_psychologist)]
