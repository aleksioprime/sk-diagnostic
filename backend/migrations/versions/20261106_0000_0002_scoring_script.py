"""Скрипт расчёта и признак «нужна дата рождения» в методике

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-06 12:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('tests', sa.Column('needs_birth_date', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('tests', sa.Column('scoring_script', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tests', 'scoring_script')
    op.drop_column('tests', 'needs_birth_date')
