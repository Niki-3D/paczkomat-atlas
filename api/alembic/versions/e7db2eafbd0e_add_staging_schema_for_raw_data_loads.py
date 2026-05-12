"""add staging schema for raw data loads

Revision ID: e7db2eafbd0e
Revises: cb36d9c54133
Create Date: 2026-05-13 00:01:24.568416

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e7db2eafbd0e'
down_revision: Union[str, Sequence[str], None] = 'cb36d9c54133'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS staging CASCADE")
