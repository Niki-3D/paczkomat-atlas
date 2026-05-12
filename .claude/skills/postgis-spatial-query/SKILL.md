---
name: postgis-spatial-query
description: Use when writing PostGIS queries — spatial joins, density aggregations, radius lookups.
allowed-tools: Read, Edit, Write, Bash, Glob
---

1. Check `docs/DATA_MODEL.md` for current schema.
2. PL queries → EPSG:2180. Pan-EU → EPSG:3035 or geography.
3. Always include GIST index in DDL.
4. `ST_DWithin(geom, point, radius)` for radius, never `ST_Distance < x`.
5. `ST_Within(point_geom, polygon_geom)` for point-in-polygon.
6. Materialize density aggregations into `mv_*` with concurrent refresh.
7. EXPLAIN ANALYZE before delivering.
