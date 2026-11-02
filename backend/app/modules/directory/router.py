"""Поиск сотрудников в справочнике: кого назначить в психологическую службу."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sk_common.deps import AdminUser, Db
from sk_common.people.models import Person
from sqlalchemy import or_, select

router = APIRouter(prefix='/v1/directory', tags=['directory'])


class PersonBrief(BaseModel):
    id: int
    full_name: str
    email: str | None
    departments: list[str]


@router.get('/employees', response_model=list[PersonBrief], summary='Найти сотрудника')
async def search_employees(
    db: Db, _: AdminUser, q: Annotated[str, Query(min_length=2, max_length=100)]
) -> list[PersonBrief]:
    pattern = f'%{q.strip()}%'
    rows = await db.scalars(
        select(Person)
        .where(
            Person.is_employee.is_(True),
            Person.is_active.is_(True),
            Person.email.is_not(None),
            or_(Person.last_name.ilike(pattern), Person.first_name.ilike(pattern), Person.email.ilike(pattern)),
        )
        .order_by(Person.last_name, Person.first_name)
        .limit(20)
    )
    return [
        PersonBrief(id=p.id, full_name=p.full_name, email=p.email, departments=[d.name for d in p.departments])
        for p in rows.unique()
    ]
