from datetime import datetime

from sk_common.db import Base
from sk_common.people.models import User
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Psychologist(Base):
    """Сотрудник психологической службы: выдаёт методики и видит результаты. Назначает администратор."""

    __tablename__ = 'psychologists'

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(lazy='joined')
