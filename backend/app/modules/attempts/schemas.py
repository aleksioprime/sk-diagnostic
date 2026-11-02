from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ScaleOptionOut(ORMModel):
    id: int
    label: str
    description: str
    value: str


class OptionOut(ORMModel):
    id: int
    label: str
    description: str
    value: str


class QuestionOut(ORMModel):
    id: int
    order: int
    code: str | None
    text: str
    description: str
    question_type: str
    is_required: bool
    is_random: bool
    min_selections: int | None
    max_selections: int | None
    options: list[OptionOut]
    scale_options: list[ScaleOptionOut] = []


class TestOut(ORMModel):
    id: int
    title: str
    code: str
    description: str
    is_sequential: bool


class TestBrief(ORMModel):
    id: int
    title: str
    code: str
    description: str
    questions_count: int = 0
    needs_birth_date: bool = False


class AnswerIn(BaseModel):
    option_id: int | None = None
    scale_option_id: int | None = None
    text: str | None = Field(default=None, max_length=5000)
    number: float | None = None
    boolean: bool | None = None
    ranking: list[int] = Field(default=[], max_length=50)


class AnswerOut(ORMModel):
    question_id: int
    option_id: int | None
    scale_option_id: int | None
    text: str | None
    number: float | None
    boolean: bool | None
    ranking_ids: list[int]


class StartIn(BaseModel):
    birth_date: date | None = None


class MyAttemptBrief(BaseModel):
    id: int
    status: str
    assignment_title: str
    test: TestOut
    started_at: datetime | None
    submitted_at: datetime | None
    is_open: bool
    needs_birth_date: bool


class MyAttemptOut(MyAttemptBrief):
    questions: list[QuestionOut]
    answers: list[AnswerOut]
