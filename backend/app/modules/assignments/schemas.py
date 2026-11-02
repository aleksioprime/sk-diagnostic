from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClassOut(ORMModel):
    id: int
    name: str
    grade: int | None
    academic_year: str | None = None
    students_count: int = 0


class AssignmentIn(BaseModel):
    test_id: int
    class_id: int
    title: str = Field(default='', max_length=500)


class AssignmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    is_active: bool | None = None
    closes_at: datetime | None = None


class AssignmentOut(BaseModel):
    id: int
    title: str
    test_id: int
    test_title: str
    test_code: str
    class_id: int | None
    class_name: str | None
    is_active: bool
    closes_at: datetime | None
    created_at: datetime
    total: int = 0
    assigned: int = 0
    in_progress: int = 0
    submitted: int = 0


class StudentOut(BaseModel):
    person_id: int
    full_name: str
    class_name: str | None
    birth_date: date | None
    gender: str | None


class AttemptRow(BaseModel):
    id: int
    status: str
    student: StudentOut
    started_at: datetime | None
    submitted_at: datetime | None
    duration: int | None
    result_status: str | None
    result_error: str | None
    summary: dict


class AssignmentDetail(AssignmentOut):
    attempts: list[AttemptRow]


class AnswerView(BaseModel):
    question_id: int
    order: int
    text: str
    question_type: str
    answer: str | None


class AttemptDetail(AttemptRow):
    assignment_id: int
    assignment_title: str
    test_code: str
    test_title: str
    result: dict | None
    answers: list[AnswerView]


class AddStudentsIn(BaseModel):
    person_ids: list[int] = Field(min_length=1, max_length=100)


class BirthDateIn(BaseModel):
    birth_date: date | None


class PsychologistOut(BaseModel):
    user_id: int
    person_id: int | None
    full_name: str
    email: str


class PsychologistsIn(BaseModel):
    person_ids: list[int] = Field(max_length=100)
