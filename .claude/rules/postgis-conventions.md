# PostGIS Conventions

## SRIDs
- Storage: 4326 (geography for points).
- PL distance ops: 2180 (PUWG 1992 / Poland CS92).
- EU pan-region: 3035 (LAEA Europe).
- Web Mercator (3857): tile generation only.

## Tables
- `lockers (id, name, country, geom geography(Point,4326), gmina_id, nuts2_id, raw jsonb, ...)`
- `gminy (teryt PK, name, geom geometry(MultiPolygon,2180))`
- `nuts2 (code PK, name, country, geom geometry(MultiPolygon,4326))`
- `population_gmina (teryt FK, year, value bigint)`
- `population_nuts2 (code FK, year, value bigint)`
- `mv_density_gmina` — materialized: lockers per 10k inhabitants per gmina
- `mv_density_nuts2` — same for EU

## Indexing
- GIST on every geom/geography column.
- BRIN on `created_at` for future time-series.

## Operators
- Radius: `ST_DWithin(geom, ST_MakePoint(lon,lat)::geography, meters)`.
- Point-in-polygon: `ST_Within(ST_Transform(p.geom::geometry, 2180), g.geom)`.

## Materialized views
- All density/aggregation queries hit MVs.
- Refresh: `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_*` (needs UNIQUE index).
- Cron daily after ingest.
