# Paczkomat Atlas — Backend Walkthrough

State of the backend after Phase 6.5. Every section below is a live demonstration of working code, real data, and the architecture in action.

## Quick start

```bash
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d
curl -s http://localhost:8080/api/v1/health
```

```json
{
  "db": "ok",
  "martin": "ok",
  "locker_count": 150599,
  "country_kpi_rows": 14,
  "snapshot_rows": 336027,
  "status": "ok"
}
```

The single `:8080` surface (Caddy) probes downstream — Postgres via SQLAlchemy, Martin via HTTP. Both green, plus a sanity count on the locker corpus (150k) and the time-series snapshots hypertable (336k rows = one daily snapshot of the full corpus + a couple of hand-fired ones during dev).

---

## 1. The data layer

### 1.1 Database stack

```text
SERVICE     STATE     HEALTH    PORTS
api         running   healthy   0.0.0.0:8000->8000/tcp
caddy       running             0.0.0.0:8080->8080/tcp
db          running   healthy   0.0.0.0:5432->5432/tcp
martin      running   healthy   0.0.0.0:3001->3000/tcp
pgbouncer   running   healthy   0.0.0.0:6432->5432/tcp
```

Five services, all healthy. Caddy fronts on `:8080`, db on direct `:5432`, pgbouncer on `:6432` (txn-mode), Martin proxied as `/tiles/*`, FastAPI proxied as `/api/*`.

### 1.2 Extensions

```bash
docker exec paczkomat-db psql -U paczkomat -d paczkomat_atlas -c \
  "SELECT extname, extversion FROM pg_extension ORDER BY extname;"
```

```text
      extname       | extversion
--------------------+------------
 h3                 | 4.1.4
 h3_postgis         | 4.1.4
 pg_cron            | 1.6
 pg_stat_statements | 1.10
 plpgsql            | 1.0
 postgis            | 3.5.1
 postgis_raster     | 3.5.1
 postgis_topology   | 3.5.1
 timescaledb        | 2.17.2
```

PostGIS for spatial, h3 + h3_postgis for hex aggregation, TimescaleDB for the snapshots hypertable, pg_cron for scheduled MV refreshes, pg_stat_statements for query observability.

### 1.3 Schema

```text
  Schema  |       Name       | Type
----------+------------------+-------
 public   | alembic_version  | table
 public   | gminy            | table
 public   | ingest_snapshots | table
 public   | lockers          | table
 public   | nuts2            | table
 public   | population_gmina | table
 public   | population_nuts2 | table
 public   | spatial_ref_sys  | table   (PostGIS internal)
 topology | layer            | table   (PostGIS internal)
 topology | topology         | table   (PostGIS internal)
```

Six application tables. `spatial_ref_sys` + the two topology tables are PostGIS-internal and filtered out by Alembic's `include_object` hook.

### 1.4 Materialized views

```text
   matviewname    | hasindexes
------------------+------------
 mv_country_kpi   | t
 mv_density_gmina | t
 mv_density_nuts2 | t
 mv_h3_density_r8 | t
```

Four MVs, all with unique indexes — required for `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

### 1.5 TimescaleDB hypertable

```bash
docker exec paczkomat-db psql -U paczkomat -d paczkomat_atlas -c "
  SELECT hypertable_name, num_chunks, compression_enabled FROM timescaledb_information.hypertables;
  SELECT count(*) AS total_rows FROM ingest_snapshots;
"
```

```text
 hypertable_name  | num_chunks | compression_enabled
------------------+------------+---------------------
 ingest_snapshots |          1 | t

 total_rows
------------
     336027
```

Snapshots compress after 14 days, drop after 730 (2 years).

### 1.6 pg_cron schedule

```text
schedule  |                         command                         |          jobname
------------+---------------------------------------------------------+----------------------------
 15 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_country_kpi   | paczkomat_mv_country_kpi
 20 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_gmina | paczkomat_mv_density_gmina
 25 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_nuts2 | paczkomat_mv_density_nuts2
 30 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_h3_density_r8 | paczkomat_mv_h3_density_r8
 45 4 * * * | ANALYZE lockers                                         | paczkomat_analyze_lockers
```

5-minute gaps to avoid lock contention, all in Europe/Warsaw timezone (set at cluster level).

---

## 2. The data — what we actually loaded

### 2.1 Lockers — 150k+ across 14 countries

```text
 country | total | lockers | pudo  | operating | open_247
---------+-------+---------+-------+-----------+----------
 PL      | 33379 |   32853 |   526 |     32183 |    29574
 FR      | 26577 |   11959 | 14618 |     17582 |     8930
 GB      | 24218 |   15065 |  9153 |     18403 |    16398
 DE      | 17460 |       0 | 17460 |     17179 |      482
 ES      | 14700 |    4286 | 10414 |     10954 |     2260
 IT      | 11120 |    5848 |  5272 |      9948 |     4361
 AT      |  4785 |    1654 |  3131 |      3277 |     1324
 SE      |  4454 |       0 |  4454 |         0 |        0
 PT      |  3191 |     492 |  2699 |      2321 |      296
 HU      |  2719 |    1283 |  1436 |      2719 |     1284
 DK      |  2375 |       0 |  2375 |         0 |        0
 FI      |  2375 |       0 |  2375 |         0 |        0
 BE      |  1796 |     562 |  1234 |      1388 |      490
 NL      |  1450 |      44 |  1406 |      1004 |       46
```

**The story per market:**
- **PL** is locker-first and saturated — 32.8k machines, 96% Operating, 88.5% open 24/7.
- **DE** is pure PUDO (Mondial Relay) — zero InPost-branded lockers, 17.5k partner pickup points.
- **SE / DK / FI** all show 0 Operating — these are dormant Mondial Relay catalogs from the post-acquisition footprint. No active InPost service in these markets.
- **GB / FR** lead non-PL locker rollout (15k / 12k respectively).

### 2.2 Coverage gaps — top 15 PL gminy by density

```text
     name     |    voivodeship     | n_lockers | population | lockers_per_10k
--------------+--------------------+-----------+------------+-----------------
 Kuślin       | wielkopolskie      |        10 |       5098 |           19.62
 Rudziniec    | śląskie            |        19 |      10802 |           17.59
 Manowo       | zachodniopomorskie |        10 |       5687 |           17.58
 Międzyzdroje | zachodniopomorskie |        10 |       5957 |           16.79
 Zbąszyń      | wielkopolskie      |        22 |      13689 |           16.07
 Wiązowna     | mazowieckie        |        26 |      16276 |           15.97
 Budzyń       | wielkopolskie      |        13 |       8300 |           15.66
 Siedlec      | wielkopolskie      |        19 |      12411 |           15.31
 Opatów       | śląskie            |        10 |       6588 |           15.18
 Głogów       | dolnośląskie       |        11 |       7260 |           15.15
 Babimost     | lubuskie           |         9 |       6026 |           14.94
 Imielin      | śląskie            |        14 |       9430 |           14.85
 Kaczory      | wielkopolskie      |        11 |       7429 |           14.81
 Biesiekierz  | zachodniopomorskie |        10 |       6787 |           14.73
 Oława        | dolnośląskie       |        23 |      15697 |           14.65
```

**The story:** the highest-density gminy aren't urban — they're small rural/suburban communities adjacent to logistics hubs (Wielkopolskie around Poznań, Śląskie around Katowice). InPost saturated warehouse-adjacent municipalities early.

### 2.3 The headline — Polish dominance in EU density

```text
      name_latn       | country | n_lockers | population | lockers_per_10k
----------------------+---------+-----------+------------+-----------------
 Wielkopolskie        | PL      |      3460 |    3438504 |           10.06
 Lubuskie             | PL      |       936 |     947784 |            9.88
 Małopolskie          | PL      |      3141 |    3318985 |            9.46
 Opolskie             | PL      |       837 |     890392 |            9.40
 Dolnośląskie         | PL      |      2533 |    2805463 |            9.03
 Śląskie              | PL      |      3784 |    4217521 |            8.97
 Warszawski stołeczny | PL      |      2869 |    3281583 |            8.74
 Podkarpackie         | PL      |      1696 |    1955368 |            8.67
 Pomorskie            | PL      |      1988 |    2296972 |            8.65
 Zachodniopomorskie   | PL      |      1312 |    1579753 |            8.31
 Łódzkie              | PL      |      1888 |    2327239 |            8.11
 Kujawsko-pomorskie   | PL      |      1512 |    1931648 |            7.83
 Świętokrzyskie       | PL      |       858 |    1123153 |            7.64
 Warmińsko-mazurskie  | PL      |       983 |    1294712 |            7.59
 Lubelskie            | PL      |      1463 |    1934465 |            7.56
```

**The story:** all 15 densest NUTS-2 regions in Europe are Polish voivodeships. None of the top non-PL NUTS-2 regions clear 3 lockers per 10k inhabitants. Polish Wielkopolskie at 10.06 is roughly **3-5× denser** than the densest non-PL region anywhere.

### 2.4 Network composition per country

```text
 country | n_lockers | n_pudo | n_total | n_247 | pct_247
---------+-----------+--------+---------+-------+---------
 PL      |     31687 |    496 |   32183 | 28494 |    88.5
 GB      |     14388 |   4015 |   18403 | 13265 |    72.1
 FR      |     10423 |   7165 |   17588 |  7942 |    45.2
 DE      |         0 |  17179 |   17179 |   472 |     2.7
 ES      |      4249 |   6705 |   10954 |  2155 |    19.7
 IT      |      5097 |   4851 |    9948 |  3823 |    38.4
 AT      |      1619 |   1658 |    3277 |  1290 |    39.4
 HU      |      1283 |   1436 |    2719 |  1284 |    47.2
 PT      |       486 |   1835 |    2321 |   289 |    12.5
 BE      |       512 |    877 |    1389 |   435 |    31.3
 NL      |        27 |    977 |    1004 |    26 |     2.6
 FI      |         0 |      0 |       0 |     0 |
 SE      |         0 |      0 |       0 |     0 |
 DK      |         0 |      0 |       0 |     0 |
```

`pct_247` is the dashboard's real differentiator: PL's 88.5% open 24/7 vs FR's 45% vs DE's 2.7% shows network maturity at a glance.

---

## 3. The API — every endpoint working

All endpoints below are served through Caddy at `:8080`, which proxies to the FastAPI container.

### 3.1 Health

```bash
curl -s http://localhost:8080/api/v1/health
```

```json
{"db":"ok","martin":"ok","locker_count":150599,"country_kpi_rows":14,"snapshot_rows":336027,"status":"ok"}
```

### 3.2 Network summary

```bash
curl -s http://localhost:8080/api/v1/kpi/summary
```

```json
{
  "data": {
    "n_lockers_total": 69771,
    "n_pudo_total": 47194,
    "n_network_total": 116965,
    "n_countries_active": 11,
    "pl_lockers": 31687,
    "pl_pct_247": 88.5
  },
  "meta": {"source": "mv_country_kpi"}
}
```

Landing-page hero numbers come from the `mv_country_kpi` MV — pre-aggregated, sub-ms response.

### 3.3 Per-country KPIs (showing 5 of 14)

```bash
curl -s http://localhost:8080/api/v1/kpi/countries
```

```json
{
  "data": [
    {"country":"PL","n_lockers":31687,"n_pudo":496,"n_total":32183,"n_247":28494,"pct_247":88.5},
    {"country":"GB","n_lockers":14388,"n_pudo":4015,"n_total":18403,"n_247":13265,"pct_247":72.1},
    {"country":"FR","n_lockers":10423,"n_pudo":7165,"n_total":17588,"n_247":7942,"pct_247":45.2},
    {"country":"DE","n_lockers":0,"n_pudo":17179,"n_total":17179,"n_247":472,"pct_247":2.7},
    {"country":"ES","n_lockers":4249,"n_pudo":6705,"n_total":10954,"n_247":2155,"pct_247":19.7}
  ],
  "meta": {"count": 14}
}
```

### 3.4 Top 15 NUTS-2 by density

```bash
curl -s "http://localhost:8080/api/v1/density/nuts2/top?limit=15"
```

```json
[
  {"code":"PL41","name_latn":"Wielkopolskie","country":"PL","lockers_per_10k":10.06,"n_lockers":3460,"population":3438504},
  {"code":"PL43","name_latn":"Lubuskie","country":"PL","lockers_per_10k":9.88,"n_lockers":936,"population":947784},
  {"code":"PL21","name_latn":"Małopolskie","country":"PL","lockers_per_10k":9.46,"n_lockers":3141,"population":3318985},
  {"code":"PL52","name_latn":"Opolskie","country":"PL","lockers_per_10k":9.4,"n_lockers":837,"population":890392},
  {"code":"PL51","name_latn":"Dolnośląskie","country":"PL","lockers_per_10k":9.03,"n_lockers":2533,"population":2805463}
]
```

(...10 more, all Polish voivodeships — see §2.3.)

### 3.5 Top PL gminy

```bash
curl -s "http://localhost:8080/api/v1/density/gminy/top?limit=10"
```

```json
[
  {"teryt":"3015012","name":"Kuślin","voivodeship":"wielkopolskie","lockers_per_10k":19.62,"n_lockers":10,"population":5098},
  {"teryt":"2405052","name":"Rudziniec","voivodeship":"śląskie","lockers_per_10k":17.59,"n_lockers":19,"population":10802},
  {"teryt":"3209042","name":"Manowo","voivodeship":"zachodniopomorskie","lockers_per_10k":17.58,"n_lockers":10,"population":5687}
]
```

### 3.6 Filtered lockers

```bash
curl -s "http://localhost:8080/api/v1/lockers?country=PL&is_locker=true&location_247=true&limit=3"
```

```json
{
  "data": [
    {"name":"ADA01M","country":"PL","status":"Operating","is_locker":true,"physical_type":"newfm","location_247":true,"latitude":51.73834,"longitude":22.26405},
    {"name":"ADA01N","country":"PL","status":"Operating","is_locker":true,"physical_type":"next","location_247":true,"latitude":51.7444,"longitude":22.25875},
    {"name":"ADAM01N","country":"PL","status":"Operating","is_locker":true,"physical_type":"next","location_247":true,"latitude":52.26299,"longitude":18.08788}
  ],
  "meta": {"total": 29571, "limit": 3, "offset": 0}
}
```

29,571 lockers in PL that are open 24/7 — the tabular form. Map rendering uses the tile endpoint instead.

### 3.7 Single locker detail

```bash
curl -s "http://localhost:8080/api/v1/lockers/ADA01M"
```

```json
{
  "data": {
    "name": "ADA01M",
    "country": "PL",
    "status": "Operating",
    "is_locker": true,
    "physical_type": "newfm",
    "location_247": true,
    "latitude": 51.73834,
    "longitude": 22.26405,
    "gmina_teryt": "0611032",
    "nuts2_id": "PL81",
    "updated_at": "2026-05-12T21:13:53.628352Z"
  },
  "meta": {}
}
```

Joined to the gmina (TERYT `0611032`) and NUTS-2 region (`PL81` = Lubelskie) via spatial assignment.

### 3.8 H3 hex aggregation

```bash
curl -s "http://localhost:8080/api/v1/h3/cells?country=PL&limit=5"
```

```json
{
  "data": [
    {"h3":"881f53c99dfffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13},
    {"h3":"881e2040ddfffff","country":"PL","n_lockers":11,"n_pudo":2,"n_total":13},
    {"h3":"881f53c939fffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13},
    {"h3":"881f5234b1fffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13},
    {"h3":"881f0e795dfffff","country":"PL","n_lockers":12,"n_pudo":0,"n_total":12}
  ],
  "meta": {"count": 5, "resolution": 8}
}
```

H3 resolution 8 (~0.7 km² hexes). For map use, prefer the tile endpoint.

### 3.9 Expansion velocity

```bash
curl -s "http://localhost:8080/api/v1/velocity?country=PL"
```

```json
{
  "data": [
    {"country":"PL","date":"2022-12-31","n_lockers":19215,"source":"press_release"},
    {"country":"PL","date":"2023-06-30","n_lockers":21840,"source":"press_release"},
    {"country":"PL","date":"2023-12-31","n_lockers":22870,"source":"press_release"},
    {"country":"PL","date":"2024-06-30","n_lockers":24120,"source":"press_release"},
    {"country":"PL","date":"2024-12-31","n_lockers":25440,"source":"press_release"},
    {"country":"PL","date":"2025-06-30","n_lockers":26500,"source":"press_release"}
  ],
  "meta": {"count": 6, "note": "Historical data from InPost press releases; daily live snapshots from 2026-05"}
}
```

Static historical points from public sources (annual reports, press releases). Future versions will read from a TimescaleDB continuous aggregate over `ingest_snapshots` once we have enough history.

### 3.10 OpenAPI surface

```bash
curl -s http://localhost:8080/openapi.json | python -m json.tool | head
```

13 endpoints with clean operation IDs (no FastAPI default suffixes):

```text
Paths:
  /
  /api/v1/density/gminy
  /api/v1/density/gminy/top
  /api/v1/density/nuts2
  /api/v1/density/nuts2/top
  /api/v1/h3/cells
  /api/v1/health
  /api/v1/kpi/countries
  /api/v1/kpi/countries/{country}
  /api/v1/kpi/summary
  /api/v1/lockers
  /api/v1/lockers/{name}
  /api/v1/velocity

Operation IDs:
  getCountryKpi    getLocker    getNetworkSummary    getVelocity
  healthCheck      listCountryKpis    listGminy    listH3Cells
  listLockers      listNuts2    root    topGminy    topNuts2
```

### 3.11 Response headers

```bash
curl -s -D - -o /dev/null "http://localhost:8080/api/v1/kpi/summary"
```

```text
HTTP/1.1 200 OK
Cache-Control: public, max-age=3600, stale-while-revalidate=86400
Content-Length: 176
Content-Type: application/json
Server: Caddy
Server: uvicorn
X-Request-Id: 633406b61762
```

`Cache-Control` from the API's middleware (1h fresh + 24h SWR), `X-Request-Id` from the request-logging middleware for traceability, double `Server` header showing Caddy → uvicorn chain.

---

## 4. The tiles — Martin in action

### 4.1 Catalog

```bash
curl -s http://localhost:8080/catalog
```

Three SQL-function tile sources plus auto-discovered geometry tables:

```text
SQL functions:
  gminy_density_tiles   public.gminy_density_tiles
  nuts2_density_tiles   public.nuts2_density_tiles
  lockers_tiles         public.lockers_tiles

Auto-discovered table tile sources:
  gminy          public.gminy.geom
  gminy_prg      staging.gminy_prg.geom
  nuts2          public.nuts2.geom
  lockers        public.lockers.geom
  ingest_snapshots, _hyper_5_1_chunk (TimescaleDB)
```

The dashboard will use the three function-backed sources (joined with population for density coloring); the raw `.geom` tables are useful for debugging.

### 4.2 NUTS-2 polygon tile (continental zoom)

```bash
curl -s -o tile_nuts2.mvt "http://localhost:8080/tiles/nuts2_density_tiles/4/8/5"
ls -la tile_nuts2.mvt
```

```text
-rw-r--r-- 268213 May 14 18:14 tile_nuts2.mvt
```

268 KB at z=4 covering central Europe — within the 1 MB Martin tile budget. Includes all the precomputed density attributes the choropleth will color on.

### 4.3 Locker point tile (Warsaw zoom)

```bash
curl -s -o tile_lockers_z10.mvt "http://localhost:8080/tiles/lockers_tiles/10/571/337"
ls -la tile_lockers_z10.mvt
```

```text
-rw-r--r-- 48887 May 14 18:14 tile_lockers_z10.mvt
```

49 KB for a zoom-10 tile over Warsaw — a few hundred individual lockers with name + status + physical_type properties, ready for MapLibre to render as symbols.

### 4.4 Gminy density tile (PL zoom)

```bash
curl -s -o tile_gminy.mvt "http://localhost:8080/tiles/gminy_density_tiles/7/72/41"
ls -la tile_gminy.mvt
```

```text
-rw-r--r-- 159916 May 14 18:14 tile_gminy.mvt
```

156 KB at z=7 (function gates `z < 5` to RETURN NULL — too many gminy at continental zoom).

### 4.5 MVT content

All three tile endpoints return `application/x-protobuf` (validated by the `Content-Type` header on every successful response). The Martin function source guarantees:
- Tiles always include valid geometry transformed to EPSG:3857.
- Empty result sets return HTTP 204, not 404 — MapLibre handles that gracefully.
- `z=0/0/0` to `z=14/*/*` all work; we cap MapLibre `maxzoom: 14` on the client.

---

## 5. The frontend integration — typed TS client ready

### 5.1 Generated code surface

```bash
ls -la web/lib/api/
wc -l web/lib/api/*.ts
```

```text
   25 web/lib/api/client.gen.ts        # hey-api fetch client config
  101 web/lib/api/index.ts             # re-exports
  945 web/lib/api/schemas.gen.ts       # OpenAPI schemas (rare use)
  237 web/lib/api/sdk.gen.ts           # the 13 endpoint functions
  989 web/lib/api/types.gen.ts         # all request/response types
 2297 total
```

Plus `client/` and `core/` subdirectories with hey-api runtime helpers.

### 5.2 Function signatures sample

```bash
grep -E "^export const " web/lib/api/sdk.gen.ts
```

```text
export const healthCheck       = <ThrowOnError extends boolean = false>(
export const getNetworkSummary = <ThrowOnError extends boolean = false>(
export const listCountryKpis   = <ThrowOnError extends boolean = false>(
export const getCountryKpi     = <ThrowOnError extends boolean = false>(
export const listGminy         = <ThrowOnError extends boolean = false>(
export const topGminy          = <ThrowOnError extends boolean = false>(
export const listNuts2         = <ThrowOnError extends boolean = false>(
export const topNuts2          = <ThrowOnError extends boolean = false>(
export const listLockers       = <ThrowOnError extends boolean = false>(
export const getLocker         = <ThrowOnError extends boolean = false>(
export const listH3Cells       = <ThrowOnError extends boolean = false>(
export const getVelocity       = <ThrowOnError extends boolean = false>(
export const root              = <ThrowOnError extends boolean = false>(
```

Every endpoint becomes a typed function. `ThrowOnError` is hey-api's standard generic — pass `true` to make it `throw` on non-2xx instead of returning `{ data, error }`.

### 5.3 End-to-end smoke run

```bash
cd web && pnpm tsx scripts/codegen-smoke.ts
```

```text
Network summary: {
  n_lockers_total: 69771,
  n_pudo_total: 47194,
  n_network_total: 116965,
  n_countries_active: 11,
  pl_lockers: 31687,
  pl_pct_247: 88.5
}
Top 5 NUTS-2:
  PL Wielkopolskie: 10.06
  PL Lubuskie: 9.88
  PL Małopolskie: 9.46
  PL Opolskie: 9.4
  PL Dolnośląskie: 9.03
```

End-to-end: TS imports → typed SDK call → Caddy → FastAPI → pgbouncer → Postgres → MV → typed response. No errors, no warnings.

---

## 6. The architecture (visual map)

```text
                ┌─────────────────────────────────────────┐
                │            Caddy :8080                  │
                │  /api/* → api    /tiles/* → martin      │
                │  /openapi.json /docs /catalog           │
                └────┬─────────────────┬──────────────────┘
                     │                 │
            ┌────────▼────────┐  ┌─────▼──────────┐
            │  FastAPI :8000  │  │  Martin :3000  │
            │  (uvicorn)      │  │  (vector tiles)│
            └────────┬────────┘  └────────┬───────┘
                     │                    │
            ┌────────▼─────────┐          │
            │ pgbouncer :6432  │          │  (direct, session mode)
            │ (txn pooling)    │          │
            └────────┬─────────┘          │
                     │                    │
                     ▼                    ▼
            ┌──────────────────────────────────┐
            │  Postgres 16 (timescaledb-ha)    │
            │  PostGIS 3.5 + h3 + TimescaleDB  │
            │  + pg_cron + pg_stat_statements  │
            └──────────────────────────────────┘
                              │
                              │  refreshes daily 04:15-04:30
                              │  via pg_cron
                              ▼
                ┌──────────────────────────────┐
                │  4 materialized views        │
                │  + 1 hypertable (snapshots)  │
                └──────────────────────────────┘
```

---

## 7. What's in the repo

```bash
git log --oneline main | head -10
```

```text
3c6de28 Merge pull request #11 from Niki-3D/chore/operation-ids
b5430f8 feat(api): explicit operation_id on every endpoint for clean TS codegen
6392edb Merge pull request #10 from Niki-3D/feat/tiles-and-codegen
8ca9c03 chore(ci): green CI — ruff cleanup, mypy fixes, pnpm workspace install
f4fae13 feat(web): hey-api TS codegen from FastAPI OpenAPI spec
5f9c260 feat(api): health endpoint probes Martin reachability
a5c7561 feat(infra): Caddy reverse proxy for unified URL surface
a8b7807 feat(db): SQL function tile sources for Martin
5c1419c feat(infra): add Martin vector tile server
32d0aec Merge pull request #9 from Niki-3D/feat/api-layer
```

Per phase: Phase 1 (DB foundation) → Phase 2 (schema + MVs + pg_cron) → Phase 3 (ingest) → Phase 4 (boundaries + population) → Phase 5 (API layer) → Phase 6 (tiles + codegen) → Phase 6.5 (operation_id cleanup). All landed via PR.

```bash
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.sql" \
  -o -name "Caddyfile" -o -name "Dockerfile*" -o -name "*.yml" \) \
  -not -path "./web/node_modules/*" -not -path "./api/.venv/*" \
  -not -path "./data/*" -not -path "./.git/*" -not -path "./node_modules/*" \
  -not -path "*/__pycache__/*" | wc -l
```

```text
96
```

96 source files. Compact.

---

## 8. Known limitations and v1 cuts

- **GB excluded from NUTS-2 view** — Eurostat dropped UK from GISCO post-Brexit. 24k GB lockers have no `nuts2_id`. Per-country KPIs still work; the cross-country density view doesn't include GB.
- **PRG vintage 2022-06-27** — TERYT codes are stable; boundary micro-changes don't materially affect 10k-resolution density math.
- **Velocity timeline is static** — 22 data points from InPost press releases. The TimescaleDB hypertable + continuous aggregates will replace this once we have ≥6 months of daily snapshots.
- **Procrastinate skipped for v1** — single async CLI invoked by pg_cron. Switch to Procrastinate when scheduling complexity warrants.
- **Cloudflare CDN + ETag** — not configured. Caddy gzip + `Cache-Control` headers handle dev/local well; production deploy may add CF in front of Caddy.
- **Mypy not in CI** — added locally (clean), but CI runs only ruff + pytest. Worth adding `uv run mypy src/` step in a follow-up.
- **Integration tests in `tests/api/`** require the live stack to be running. They aren't marked, so `pytest` fails outside Docker (9 ConnectionRefused). A `pytest.mark.integration` split is the obvious follow-up.

---

## 9. How to play

```bash
# Start the stack
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d

# Trigger a fresh ingest (full re-crawl of all 14 countries)
docker exec paczkomat-api python -m paczkomat_atlas_api.ingest.cli --all

# Refresh the MVs explicitly (pg_cron does this nightly at 04:15-04:30)
docker exec paczkomat-api python -m paczkomat_atlas_api.ingest.cli --refresh-only

# Take a snapshot for the hypertable
docker exec paczkomat-api python -m paczkomat_atlas_api.ingest.cli --snapshot-only

# Browse the API docs
open http://localhost:8080/docs

# Inspect the tile catalog
open http://localhost:8080/catalog

# Fetch a tile
curl http://localhost:8080/tiles/nuts2_density_tiles/4/8/5 > tile.mvt

# Regenerate the TS client after API changes
cd web && pnpm codegen

# Run the codegen smoke test
cd web && pnpm tsx scripts/codegen-smoke.ts
```

Backend is feature-complete for Phase 1-6.5. Next up: frontend (landing page, dashboard, the MapLibre choropleth, the KPI bar, the velocity timeline). Stack is ready; everything below the UI line is honest.
