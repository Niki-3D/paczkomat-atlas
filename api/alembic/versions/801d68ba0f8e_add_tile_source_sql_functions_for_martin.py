"""add tile-source SQL functions for Martin

Revision ID: 801d68ba0f8e
Revises: e7db2eafbd0e
Create Date: 2026-05-13 23:33:47.614518

Defines three plpgsql functions that Martin auto-discovers as vector tile
sources: lockers_tiles, nuts2_density_tiles, gminy_density_tiles. Each
returns bytea (MVT-encoded) for a (z, x, y, query_params) triple and is
declared as:

    IMMUTABLE STRICT PARALLEL SAFE

Why:
- IMMUTABLE — the function output is a pure function of its inputs (no
  reads outside the call). Lets Martin's HTTP cache + Postgres planner cache
  results aggressively. Daily MV refresh invalidates downstream layers, not
  the function definition itself.
- STRICT — returns NULL if any argument is NULL. Avoids defensive null
  checks inside the body.
- PARALLEL SAFE — Postgres may execute the function in a parallel query
  worker. Our functions only touch normal tables + already-refreshed MVs,
  so parallelism is fine.

asyncpg refuses multiple statements in a single prepared statement, so each
CREATE FUNCTION and each COMMENT lives in its own op.execute() call.

gminy_density_tiles gates on z >= 5 by RETURNing NULL otherwise — at lower
zooms a single tile would contain thousands of tiny polygons, blowing the
default 1 MB tile budget.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '801d68ba0f8e'
down_revision: Union[str, Sequence[str], None] = 'e7db2eafbd0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOCKERS_TILES_FN = r"""
CREATE OR REPLACE FUNCTION lockers_tiles(
    z integer, x integer, y integer, query_params json DEFAULT '{}'::json
)
RETURNS bytea AS $$
DECLARE
    mvt bytea;
    country_filter text := query_params->>'country';
    is_locker_filter text := query_params->>'is_locker';
BEGIN
    SELECT INTO mvt ST_AsMVT(t.*, 'lockers')
    FROM (
        SELECT
            ST_AsMVTGeom(
                ST_Transform(geom::geometry, 3857),
                ST_TileEnvelope(z, x, y),
                4096, 64, true
            ) AS geom,
            name,
            country,
            is_locker::int AS is_locker,
            location_247::int AS location_247,
            physical_type
        FROM lockers
        WHERE status IN ('Operating', 'Overloaded')
          AND geom::geometry && ST_Transform(ST_TileEnvelope(z, x, y, margin => 0.0625), 4326)
          AND (country_filter IS NULL OR country = country_filter)
          AND (is_locker_filter IS NULL OR is_locker = (is_locker_filter = 'true'))
    ) AS t;

    RETURN mvt;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
"""

NUTS2_DENSITY_TILES_FN = r"""
CREATE OR REPLACE FUNCTION nuts2_density_tiles(
    z integer, x integer, y integer, query_params json DEFAULT '{}'::json
)
RETURNS bytea AS $$
DECLARE
    mvt bytea;
BEGIN
    SELECT INTO mvt ST_AsMVT(t.*, 'nuts2_density')
    FROM (
        SELECT
            ST_AsMVTGeom(
                ST_Transform(n.geom, 3857),
                ST_TileEnvelope(z, x, y),
                4096, 64, true
            ) AS geom,
            n.code,
            n.name_latn,
            n.country,
            COALESCE(d.n_lockers, 0) AS n_lockers,
            COALESCE(d.n_pudo, 0) AS n_pudo,
            COALESCE(d.population, 0) AS population,
            d.lockers_per_10k
        FROM nuts2 n
        LEFT JOIN mv_density_nuts2 d USING (code)
        WHERE n.geom && ST_Transform(ST_TileEnvelope(z, x, y, margin => 0.0625), 4326)
    ) AS t;

    RETURN mvt;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
"""

GMINY_DENSITY_TILES_FN = r"""
CREATE OR REPLACE FUNCTION gminy_density_tiles(
    z integer, x integer, y integer, query_params json DEFAULT '{}'::json
)
RETURNS bytea AS $$
DECLARE
    mvt bytea;
BEGIN
    IF z < 5 THEN
        RETURN NULL;
    END IF;

    SELECT INTO mvt ST_AsMVT(t.*, 'gminy_density')
    FROM (
        SELECT
            ST_AsMVTGeom(
                ST_Transform(g.geom, 3857),
                ST_TileEnvelope(z, x, y),
                4096, 64, true
            ) AS geom,
            g.teryt,
            g.name,
            g.voivodeship,
            COALESCE(d.n_lockers, 0) AS n_lockers,
            COALESCE(d.n_pudo, 0) AS n_pudo,
            COALESCE(d.population, 0) AS population,
            d.lockers_per_10k
        FROM gminy g
        LEFT JOIN mv_density_gmina d USING (teryt)
        WHERE g.geom && ST_Transform(ST_TileEnvelope(z, x, y, margin => 0.0625), 2180)
    ) AS t;

    RETURN mvt;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT PARALLEL SAFE
"""

COMMENTS = [
    "COMMENT ON FUNCTION lockers_tiles(integer, integer, integer, json) IS "
    "'Martin tile source: lockers point layer. "
    "query_params: country (str), is_locker (true/false).'",
    "COMMENT ON FUNCTION nuts2_density_tiles(integer, integer, integer, json) IS "
    "'Martin tile source: NUTS-2 choropleth polygons with density data joined.'",
    "COMMENT ON FUNCTION gminy_density_tiles(integer, integer, integer, json) IS "
    "'Martin tile source: PL gmina-level choropleth, zoom >= 5 only (2477 polygons).'",
]


def upgrade() -> None:
    op.execute(LOCKERS_TILES_FN)
    op.execute(NUTS2_DENSITY_TILES_FN)
    op.execute(GMINY_DENSITY_TILES_FN)
    for stmt in COMMENTS:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS gminy_density_tiles(integer, integer, integer, json)")
    op.execute("DROP FUNCTION IF EXISTS nuts2_density_tiles(integer, integer, integer, json)")
    op.execute("DROP FUNCTION IF EXISTS lockers_tiles(integer, integer, integer, json)")
