"""schedule mv refreshes via pg_cron

Revision ID: 2a08cc2a0894
Revises: d6af7bb14d60
Create Date: 2026-05-12 22:58:38.234402

Registers five pg_cron jobs to refresh the dashboard MVs daily at 04:15-04:45
Europe/Warsaw, plus a final ANALYZE on lockers at 04:45. Jobs are spaced 5
minutes apart to avoid lock contention — REFRESH MATERIALIZED VIEW
CONCURRENTLY still takes a strong-enough lock that two concurrent refreshes
could serialize on shared dependencies.

Cluster timezone is set globally; the schedules use 5-field cron syntax
("15 4 * * *") not the extended pg_cron variants.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2a08cc2a0894'
down_revision: Union[str, Sequence[str], None] = 'd6af7bb14d60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# pg_cron jobs are global to the cluster — name them with project prefix to avoid collisions.
JOBS = [
    ("paczkomat_mv_country_kpi",   "15 4 * * *", "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_country_kpi"),
    ("paczkomat_mv_density_gmina", "20 4 * * *", "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_gmina"),
    ("paczkomat_mv_density_nuts2", "25 4 * * *", "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_nuts2"),
    ("paczkomat_mv_h3_density_r8", "30 4 * * *", "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_h3_density_r8"),
    ("paczkomat_analyze_lockers",  "45 4 * * *", "ANALYZE lockers"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, schedule, command in JOBS:
        # Unschedule any previous job with the same name (idempotent re-run).
        op.execute(
            f"SELECT cron.unschedule('{name}') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = '{name}')"
        )
        op.execute(f"SELECT cron.schedule('{name}', '{schedule}', $${command}$$)")


def downgrade() -> None:
    """Downgrade schema."""
    for name, _, _ in JOBS:
        op.execute(
            f"SELECT cron.unschedule('{name}') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = '{name}')"
        )
