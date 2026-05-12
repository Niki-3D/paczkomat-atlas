"""fix mv_h3_density_r8 unique index to include country

Revision ID: cb36d9c54133
Revises: 2a08cc2a0894
Create Date: 2026-05-12 23:17:07.115183

Real-data finding from Phase 3 ingest: the MV groups by (h3_r8, country)
but the original unique index was on (h3) alone. Border H3 cells span
two countries (observed: BE/NL, DE/NL, DE/PL), producing two MV rows
with the same h3 → REFRESH CONCURRENTLY fails with UniqueViolationError.

Fix: unique index on (h3, country) to match the GROUP BY.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'cb36d9c54133'
down_revision: Union[str, Sequence[str], None] = '2a08cc2a0894'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_mv_h3_density_r8")
    op.execute("CREATE UNIQUE INDEX ux_mv_h3_density_r8 ON mv_h3_density_r8(h3, country)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_mv_h3_density_r8")
    op.execute("CREATE UNIQUE INDEX ux_mv_h3_density_r8 ON mv_h3_density_r8(h3)")
