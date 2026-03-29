from __future__ import annotations

from typing import List

from pydantic import BaseModel


class AnswerUpdatePayload(BaseModel):
    option_id: int | str | None = None
    scale_option_id: int | str | None = None
    text: str | None = None
    number: float | int | None = None
    boolean: bool | None = None
    is_skipped: bool | None = None
    options: List[int | str] | None = None
    ranking: List[int | str] | None = None
