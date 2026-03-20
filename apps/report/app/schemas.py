from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class RenderRequest(BaseModel):
    template: str = Field(..., description='Template filename from templates directory')
    filename: str = Field(..., description='Output filename without extension')
    data: Dict[str, Any] = Field(default_factory=dict, description='Context for the template')
    output: Literal['docx', 'pdf', 'xlsx'] = 'docx'
    save: bool = True

    @field_validator('template')
    @classmethod
    def validate_template(cls, value: str) -> str:
        if '..' in value or value.startswith('/'):
            raise ValueError('Unsafe template path')
        return value

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, value: str) -> str:
        safe = value.strip().replace('/', '_').replace('\\', '_')
        if not safe:
            raise ValueError('Filename is required')
        return safe


class RenderResponse(BaseModel):
    ok: bool = True
    file_id: str
    filename: str
    output: Literal['docx', 'pdf', 'xlsx']
    content_type: str
    download_url: str
    size_bytes: int
    template: str


class TemplateInfo(BaseModel):
    name: str
    ext: str
    size_bytes: int


class ErrorResponse(BaseModel):
    detail: str


class BulkRenderItem(BaseModel):
    filename: str
    data: Dict[str, Any] = Field(default_factory=dict)


class BulkRenderRequest(BaseModel):
    template: str
    output: Literal['docx', 'pdf', 'xlsx'] = 'docx'
    items: List[BulkRenderItem]


class BulkRenderResponse(BaseModel):
    ok: bool = True
    files: List[RenderResponse]
