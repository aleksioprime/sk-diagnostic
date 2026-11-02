"""Выдачи методик классам, попытки учеников, ответы и рассчитанные результаты."""

from datetime import datetime

from sk_common.db import Base, IdMixin, TimestampMixin
from sk_common.people.models import Person, StudyClass
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.tests.models import Test

STATUS_ASSIGNED = 'assigned'
STATUS_IN_PROGRESS = 'in_progress'
STATUS_SUBMITTED = 'submitted'

RESULT_CALCULATED = 'calculated'
RESULT_ERROR = 'error'


class Assignment(IdMixin, TimestampMixin, Base):
    """Выдача методики: обычно классу целиком, каждому ученику — своя попытка."""

    __tablename__ = 'assignments'

    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete='RESTRICT'), index=True)
    title: Mapped[str] = mapped_column(String(500))
    class_id: Mapped[int | None] = mapped_column(ForeignKey('classes.id', ondelete='SET NULL'))
    # Токен из NocoBase: ссылки старых выдач
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))

    test: Mapped[Test] = relationship(lazy='joined')
    study_class: Mapped[StudyClass | None] = relationship(lazy='joined')


class Attempt(IdMixin, TimestampMixin, Base):
    __tablename__ = 'attempts'
    __table_args__ = (UniqueConstraint('assignment_id', 'person_id'),)

    assignment_id: Mapped[int] = mapped_column(ForeignKey('assignments.id', ondelete='CASCADE'), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('persons.id', ondelete='CASCADE'), index=True)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_ASSIGNED, server_default=STATUS_ASSIGNED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Длительность прохождения, секунды
    duration: Mapped[int | None] = mapped_column(Integer)

    assignment: Mapped[Assignment] = relationship(lazy='joined')
    person: Mapped[Person] = relationship(lazy='joined')
    answers: Mapped[list['Answer']] = relationship(
        back_populates='attempt', cascade='all, delete-orphan', lazy='selectin'
    )
    result: Mapped['Result | None'] = relationship(
        back_populates='attempt', cascade='all, delete-orphan', lazy='selectin', uselist=False
    )


class Answer(IdMixin, TimestampMixin, Base):
    __tablename__ = 'answers'
    __table_args__ = (UniqueConstraint('attempt_id', 'question_id'),)

    attempt_id: Mapped[int] = mapped_column(ForeignKey('attempts.id', ondelete='CASCADE'), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id', ondelete='CASCADE'), index=True)
    option_id: Mapped[int | None] = mapped_column(ForeignKey('options.id', ondelete='SET NULL'))
    scale_option_id: Mapped[int | None] = mapped_column(ForeignKey('scale_options.id', ondelete='SET NULL'))
    text: Mapped[str | None] = mapped_column(Text)
    number: Mapped[float | None] = mapped_column(Float)
    boolean: Mapped[bool | None] = mapped_column(Boolean)

    attempt: Mapped[Attempt] = relationship(back_populates='answers')
    ranking: Mapped[list['RankingItem']] = relationship(
        back_populates='answer', cascade='all, delete-orphan', order_by='RankingItem.rank', lazy='selectin'
    )

    @property
    def ranking_ids(self) -> list[int]:
        return [item.option_id for item in self.ranking]


class RankingItem(IdMixin, TimestampMixin, Base):
    __tablename__ = 'answer_ranking_items'

    answer_id: Mapped[int] = mapped_column(ForeignKey('answers.id', ondelete='CASCADE'), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey('options.id', ondelete='CASCADE'))
    rank: Mapped[int] = mapped_column(Integer)

    answer: Mapped[Answer] = relationship(back_populates='ranking')


class Result(IdMixin, TimestampMixin, Base):
    """Рассчитанный результат попытки (формат — как у скриптов NocoBase) или ошибка расчёта."""

    __tablename__ = 'results'

    attempt_id: Mapped[int] = mapped_column(ForeignKey('attempts.id', ondelete='CASCADE'), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    data: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    attempt: Mapped[Attempt] = relationship(back_populates='result')
