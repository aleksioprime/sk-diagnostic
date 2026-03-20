from __future__ import annotations

import os
import uuid
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def build_output_name(filename: str, suffix: str) -> tuple[str, str]:
    file_id = str(uuid.uuid4())
    stored_filename = f'{file_id}_{filename}.{suffix}'
    return file_id, stored_filename


def guess_content_type(ext: str) -> str:
    return {
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pdf': 'application/pdf',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }[ext]


def file_size(path: str | Path) -> int:
    return os.path.getsize(path)
