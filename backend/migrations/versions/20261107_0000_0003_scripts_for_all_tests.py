"""Расчёт методик из NocoBase — скриптами в базе: встроенного расчёта больше нет

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07 00:00:00
"""
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCRIPTS = Path(__file__).resolve().parents[2] / 'app' / 'scoring' / 'scripts'
CODES = ('motivation_learning', 'domiki_emotion_primary', 'domiki_emotion_middle')


def upgrade() -> None:
    connection = op.get_bind()
    for code in CODES:
        connection.execute(
            sa.text('update tests set scoring_script = :script where code = :code and scoring_script is null'),
            {'script': (SCRIPTS / f'{code}.js').read_text(encoding='utf-8'), 'code': code},
        )
    connection.execute(sa.text("update tests set needs_birth_date = true where code = 'motivation_learning'"))


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text('update tests set scoring_script = null where code in :codes').bindparams(
        sa.bindparam('codes', expanding=True)
    ), {'codes': list(CODES)})
