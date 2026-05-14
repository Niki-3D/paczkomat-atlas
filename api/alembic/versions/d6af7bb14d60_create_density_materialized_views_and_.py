"""create density materialized views and h3 hex aggregations

Revision ID: d6af7bb14d60
Revises: 5d424a72bd30
Create Date: 2026-05-12 22:57:40.360381

Creates the four MVs that every read-side endpoint hits:

- mv_country_kpi   — one row per country with totals + 24/7 share
- mv_density_gmina — one row per gmina with lockers_per_10k
- mv_density_nuts2 — one row per NUTS-2 region with lockers_per_10k
- mv_h3_density_r8 — one row per (h3_r8, country) bucket for the heatmap

Every MV ships with a UNIQUE index — required so pg_cron's daily refresh
can use REFRESH MATERIALIZED VIEW CONCURRENTLY. Without the unique index
refresh blocks readers for seconds.

Each MV's locker filter is `status IN ('Operating', 'Overloaded')`. NEVER
include Created/Disabled in dashboard-facing MVs (see data-quality-rules.md
for the status enum semantics).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd6af7bb14d60'
down_revision: Union[str, Sequence[str], None] = '5d424a72bd30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- mv_density_gmina: lockers per 10k inhabitants per gmina ---
    op.execute("""
        CREATE MATERIALIZED VIEW mv_density_gmina AS
        SELECT
            g.teryt,
            g.name,
            g.voivodeship,
            g.powiat,
            COALESCE(p.value, 0) AS population,
            COUNT(l.id) FILTER (WHERE l.is_locker AND l.status IN ('Operating', 'Overloaded')) AS n_lockers,
            COUNT(l.id) FILTER (WHERE NOT l.is_locker AND l.status IN ('Operating', 'Overloaded')) AS n_pudo,
            CASE
                WHEN COALESCE(p.value, 0) > 0
                THEN ROUND(
                    COUNT(l.id) FILTER (WHERE l.is_locker AND l.status IN ('Operating', 'Overloaded'))::numeric
                    / p.value * 10000, 2
                )
                ELSE NULL
            END AS lockers_per_10k
        FROM gminy g
        LEFT JOIN population_gmina p
            ON p.teryt = g.teryt AND p.year = (SELECT MAX(year) FROM population_gmina WHERE teryt = g.teryt)
        LEFT JOIN lockers l
            ON l.gmina_teryt = g.teryt
        GROUP BY g.teryt, g.name, g.voivodeship, g.powiat, p.value
    """)
    op.execute("CREATE UNIQUE INDEX ux_mv_density_gmina_teryt ON mv_density_gmina(teryt)")
    op.execute("CREATE INDEX ix_mv_density_gmina_per_10k ON mv_density_gmina(lockers_per_10k DESC NULLS LAST)")

    # --- mv_density_nuts2: same shape, EU-wide ---
    op.execute("""
        CREATE MATERIALIZED VIEW mv_density_nuts2 AS
        SELECT
            n.code,
            n.name_latn,
            n.country,
            COALESCE(p.value, 0) AS population,
            COUNT(l.id) FILTER (WHERE l.is_locker AND l.status IN ('Operating', 'Overloaded')) AS n_lockers,
            COUNT(l.id) FILTER (WHERE NOT l.is_locker AND l.status IN ('Operating', 'Overloaded')) AS n_pudo,
            CASE
                WHEN COALESCE(p.value, 0) > 0
                THEN ROUND(
                    COUNT(l.id) FILTER (WHERE l.is_locker AND l.status IN ('Operating', 'Overloaded'))::numeric
                    / p.value * 10000, 2
                )
                ELSE NULL
            END AS lockers_per_10k
        FROM nuts2 n
        LEFT JOIN population_nuts2 p
            ON p.code = n.code AND p.year = (SELECT MAX(year) FROM population_nuts2 WHERE code = n.code)
        LEFT JOIN lockers l
            ON l.nuts2_id = n.code
        GROUP BY n.code, n.name_latn, n.country, p.value
    """)
    op.execute("CREATE UNIQUE INDEX ux_mv_density_nuts2_code ON mv_density_nuts2(code)")
    op.execute("CREATE INDEX ix_mv_density_nuts2_country ON mv_density_nuts2(country)")

    # --- mv_country_kpi: top-line KPIs per country ---
    op.execute("""
        CREATE MATERIALIZED VIEW mv_country_kpi AS
        SELECT
            country,
            COUNT(*) FILTER (WHERE is_locker AND status IN ('Operating', 'Overloaded')) AS n_lockers,
            COUNT(*) FILTER (WHERE NOT is_locker AND status IN ('Operating', 'Overloaded')) AS n_pudo,
            COUNT(*) FILTER (WHERE status IN ('Operating', 'Overloaded')) AS n_total,
            COUNT(*) FILTER (WHERE location_247 AND status IN ('Operating', 'Overloaded')) AS n_247,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE location_247 AND status IN ('Operating', 'Overloaded'))
                / NULLIF(COUNT(*) FILTER (WHERE status IN ('Operating', 'Overloaded')), 0),
                1
            ) AS pct_247
        FROM lockers
        GROUP BY country
    """)
    op.execute("CREATE UNIQUE INDEX ux_mv_country_kpi_country ON mv_country_kpi(country)")

    # --- mv_h3_density_r8: hex aggregation for the heatmap layer ---
    op.execute("""
        CREATE MATERIALIZED VIEW mv_h3_density_r8 AS
        SELECT
            h3_r8 AS h3,
            country,
            COUNT(*) FILTER (WHERE is_locker) AS n_lockers,
            COUNT(*) FILTER (WHERE NOT is_locker) AS n_pudo,
            COUNT(*) AS n_total,
            h3_cell_to_boundary(h3_r8)::geometry AS geom
        FROM lockers
        WHERE status IN ('Operating', 'Overloaded')
        GROUP BY h3_r8, country
    """)
    op.execute("CREATE UNIQUE INDEX ux_mv_h3_density_r8 ON mv_h3_density_r8(h3)")
    op.execute("CREATE INDEX ix_mv_h3_density_r8_geom ON mv_h3_density_r8 USING GIST(geom)")
    op.execute("CREATE INDEX ix_mv_h3_density_r8_country ON mv_h3_density_r8(country)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_h3_density_r8")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_country_kpi")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_density_nuts2")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_density_gmina")
