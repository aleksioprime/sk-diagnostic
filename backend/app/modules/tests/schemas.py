"""Методика в файле JSON: импорт и выгрузка в одном формате. Скрипт расчёта — отдельным полем."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# multiple_choice не поддерживается формой ученика и хранением ответа
ImportedType = Literal['single_choice', 'scale', 'ranking', 'text', 'number', 'yes_no']
MAX_SCRIPT = 200_000


class _Strict(BaseModel):
    """Опечатка в названии поля файла — ошибка, а не молча потерянные данные."""

    model_config = ConfigDict(extra='forbid')


class OptionFile(_Strict):
    label: str = Field(min_length=1, max_length=500)
    description: str = ''
    value: str = Field(default='', max_length=100)
    score: float | None = None


class ScaleOptionFile(OptionFile):
    label: str = Field(min_length=1, max_length=255)


class ScaleFile(_Strict):
    code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str = ''
    options: list[ScaleOptionFile] = Field(min_length=1)


class QuestionFile(_Strict):
    order: int | None = Field(default=None, description='Номер вопроса; если не задан — по порядку в файле')
    code: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=1)
    description: str = ''
    question_type: ImportedType
    is_required: bool = True
    is_random: bool = False
    min_selections: int | None = None
    max_selections: int | None = None
    scale: str | None = Field(default=None, description='Код шкалы для вопроса типа scale')
    options: list[OptionFile] = []

    @model_validator(mode='after')
    def _check_answers(self) -> 'QuestionFile':
        name = self.text[:60]
        if self.question_type == 'scale' and not self.scale:
            raise ValueError(f'Вопрос «{name}»: для типа scale укажите scale — код шкалы')
        if self.question_type in ('single_choice', 'ranking') and not self.options:
            raise ValueError(f'Вопрос «{name}»: для типа {self.question_type} нужны options')
        return self


class TestFile(_Strict):
    __test__ = False

    code: str = Field(min_length=1, max_length=100, pattern=r'^[a-z0-9_-]+$')
    title: str = Field(min_length=1, max_length=500)
    description: str = ''
    is_sequential: bool = True
    needs_birth_date: bool = False
    scoring_script: str | None = Field(default=None, max_length=MAX_SCRIPT)
    scales: list[ScaleFile] = []
    questions: list[QuestionFile] = Field(min_length=1)

    @model_validator(mode='after')
    def _check_numbers(self) -> 'TestFile':
        numbers = [q.order if q.order is not None else n for n, q in enumerate(self.questions, 1)]
        if len(set(numbers)) != len(numbers):
            raise ValueError('Номера вопросов (order) повторяются: по ним считаются шкалы')
        return self


class ImportIn(BaseModel):
    test: TestFile
    replace: bool = Field(default=False, description='Заменить методику с тем же кодом, если её ещё не выдавали')


class TestAdminBrief(BaseModel):
    __test__ = False

    id: int
    code: str
    title: str
    is_active: bool
    questions_count: int
    assignments_count: int
    # script — скрипт в методике, builtin — расчёт в коде приложения, none — результат пока не считается
    scoring: Literal['script', 'builtin', 'none']


class TestAdminDetail(TestAdminBrief):
    description: str
    needs_birth_date: bool
    scoring_script: str | None


class TestCreateIn(BaseModel):
    code: str = Field(min_length=1, max_length=100, pattern=r'^[a-z0-9_-]+$')
    title: str = Field(min_length=1, max_length=500)


class OptionIn(BaseModel):
    id: int | None = None
    label: str = Field(min_length=1, max_length=500)
    description: str = ''
    value: str = Field(default='', max_length=100)
    score: float | None = None


class QuestionIn(BaseModel):
    id: int | None = None
    code: str | None = Field(default=None, max_length=100)
    text: str = Field(min_length=1)
    description: str = ''
    question_type: str
    is_required: bool = True
    is_random: bool = False
    scale_id: int | None = None
    options: list[OptionIn] = []


class ContentIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = ''
    is_sequential: bool = True
    questions: list[QuestionIn]


class ScaleIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ''
    options: list[OptionIn] = Field(min_length=1)


class ScaleOut(BaseModel):
    id: int
    code: str | None
    title: str
    description: str
    # full — можно всё, text — только подписи, none — шкала общая с другой методикой
    mode: Literal['full', 'text', 'none']
    options: list[OptionIn]


class QuestionOut(QuestionIn):
    id: int


class ContentOut(BaseModel):
    id: int
    code: str
    title: str
    description: str
    is_sequential: bool
    # text — можно менять только тексты: методику уже выдавали или расчёт встроен в приложение
    mode: Literal['full', 'text']
    lock_reason: str | None
    questions: list[QuestionOut]
    scales: list[ScaleOut]


class TestPatch(BaseModel):
    is_active: bool | None = None
    needs_birth_date: bool | None = None


class ScriptIn(BaseModel):
    script: str | None = Field(default=None, max_length=MAX_SCRIPT)


class RunIn(BaseModel):
    script: str | None = Field(default=None, max_length=MAX_SCRIPT, description='Пусто — встроенный расчёт методики')
    input: dict


class RunOut(BaseModel):
    output: dict | None
    error: str | None
    line: int | None
    logs: list[str]
    duration_ms: int
    summary: dict
