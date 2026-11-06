"""Методики (тесты): вопросы, варианты, шкалы. Структура повторяет NocoBase, ID сохраняются при переносе."""

from sk_common.db import Base, IdMixin, TimestampMixin
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

QUESTION_TYPES = ('single_choice', 'multiple_choice', 'scale', 'ranking', 'text', 'number', 'yes_no')


class Scale(IdMixin, TimestampMixin, Base):
    """Шкала ответа: «Почти никогда … Почти всегда», цветовая шкала «Домиков»."""

    __tablename__ = 'scales'

    title: Mapped[str] = mapped_column(String(255))
    code: Mapped[str | None] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    options: Mapped[list['ScaleOption']] = relationship(
        back_populates='scale', cascade='all, delete-orphan', order_by='ScaleOption.order', lazy='selectin'
    )


class ScaleOption(IdMixin, TimestampMixin, Base):
    __tablename__ = 'scale_options'

    scale_id: Mapped[int] = mapped_column(ForeignKey('scales.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    value: Mapped[str] = mapped_column(String(100), default='', server_default='')
    score: Mapped[float | None] = mapped_column(Float)
    order: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    scale: Mapped[Scale] = relationship(back_populates='options')


class Test(IdMixin, TimestampMixin, Base):
    """Методика. Результат считает скрипт из scoring_script (app.scoring)."""

    __tablename__ = 'tests'

    title: Mapped[str] = mapped_column(String(500))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    # Вопросы по одному на экране
    is_sequential: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    # Нормы зависят от возраста: перед началом ученик указывает дату рождения
    needs_birth_date: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    # Расчёт на JavaScript (app.scoring.sandbox)
    scoring_script: Mapped[str | None] = mapped_column(Text)

    questions: Mapped[list['Question']] = relationship(
        back_populates='test', cascade='all, delete-orphan', order_by='Question.order', lazy='selectin'
    )


class Question(IdMixin, TimestampMixin, Base):
    __tablename__ = 'questions'

    test_id: Mapped[int] = mapped_column(ForeignKey('tests.id', ondelete='CASCADE'), index=True)
    # Номер вопроса в методике: по нему считаются шкалы
    order: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    code: Mapped[str | None] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    question_type: Mapped[str] = mapped_column(String(30))
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    # Варианты в случайном порядке (цвета в «Домиках»)
    is_random: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    min_selections: Mapped[int | None] = mapped_column(Integer)
    max_selections: Mapped[int | None] = mapped_column(Integer)
    scale_id: Mapped[int | None] = mapped_column(ForeignKey('scales.id', ondelete='SET NULL'))

    test: Mapped[Test] = relationship(back_populates='questions')
    scale: Mapped[Scale | None] = relationship(lazy='selectin')
    options: Mapped[list['Option']] = relationship(
        back_populates='question', cascade='all, delete-orphan', order_by='Option.order', lazy='selectin'
    )


class Option(IdMixin, TimestampMixin, Base):
    __tablename__ = 'options'

    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    value: Mapped[str] = mapped_column(String(100), default='', server_default='')
    score: Mapped[float | None] = mapped_column(Float)
    order: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    question: Mapped[Question] = relationship(back_populates='options')
