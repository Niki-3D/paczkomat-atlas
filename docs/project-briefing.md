# Paczkomat Atlas — Project Briefing

> A 360° view of the project: what it is, what it does, what's inside, how it works, what the data looks like, and what the frontend needs to render.

Generated 2026-05-14 from a live backend. Every number, every JSON sample, every row count is real data fetched while writing this document — not transcribed from notes.

---

## 1. The project in one paragraph

InPost operates 150k+ parcel lockers and pickup points across 14 European countries. This project ingests the public InPost API, joins it against Polish gmina boundaries (PRG), EU NUTS-2 regions (Eurostat GISCO), GUS BDL population data, and Eurostat population data, then exposes a JSON+MVT API surface for an analytics dashboard. The dashboard's job: surface the gap between marketing claims and operational reality, with locker density per 10k inhabitants as the central metric.

Submitted as the InPost Technology Internship 2026 task. Deadline: 2026-05-16 Friday 23:59.

---

## 2. The thesis (what the dashboard is supposed to prove)

Three claims the data substantiates:

1. **Polish dominance is extreme.** All 15 densest NUTS-2 regions in Europe are Polish voivodeships. The first non-PL region (Budapest, HU) is at **2.24** lockers per 10k inhabitants; Poland's Wielkopolskie is at **10.06**. PL is **4.5×** denser than the densest non-PL region. The 16th-ranked region globally is still Polish.

2. **Network mix differs sharply per country.** PL is 98% lockers (saturated machine network). DE is 100% PUDO via the Mondial Relay acquisition — zero native lockers. FR is 45% lockers and rising fast. Nordic markets (SE/DK/FI) are pre-launch — catalog rows exist but zero operational lockers.

3. **Coverage is concentrated near logistics hubs, not cities.** Top PL gminy by density are small rural/suburban communities adjacent to large warehouses (Kuślin 19.62, Rudziniec 17.59, Manowo 17.58). Urban density is high but rural saturation around fulfilment hubs is higher per capita.

---

## 3. Architecture diagram and data flow

```text
External sources                  Ingest pipeline               Storage
──────────────────                ───────────────               ───────
InPost public API   ──┐
(150k records)        │
                      │  filter → upsert → spatial join
PRG shapefile         │  ↓                                     Postgres 16
(2477 gminy, ogr2ogr) ┼──→  paczkomat_atlas_api.ingest    ──→  PostGIS 3.5
                      │     (Python async CLI)                 h3 4.1.4
Eurostat NUTS-2       │                                        TimescaleDB 2.17
(299 polygons)        │                                        pg_cron 1.6
                      │                                          │
GUS BDL population    │                                          │
(BDL ID → TERYT match)│                                          │
                      │                                          ▼
Eurostat population ──┘                                    ┌──────────────┐
                                                           │ 7 tables     │
                                                           │ 4 matviews   │
                                                           │ 1 hypertable │
                                                           └──────┬───────┘
                                                                  │
                                                                  ▼
                              Caddy :8080 (reverse proxy)
                              ├─ /api/* → FastAPI (13 routes)
                              ├─ /tiles/* → Martin (3 SQL function sources)
                              └─ /catalog, /docs, /openapi.json
                                                                  │
                                                                  ▼
                              Frontend (Next.js, Phase 8)
                              ├─ hey-api TS client (typed)
                              └─ MapLibre GL JS (vector tiles)
```

### Why each component

- **Postgres 16 + PostGIS + h3 + TimescaleDB** — single-database stack. Spatial joins (PostGIS), hex indexing for the heatmap (h3), time-series hypertable for daily snapshots (TimescaleDB), and job scheduling for materialized view refreshes (pg_cron). All in one image (`timescaledb-ha:pg16.6-ts2.17.2-all`).
- **pgbouncer transaction pool** — async SQLAlchemy under burst load hammers connection limits. Pgbouncer pools at the transaction level, prepared statement cache disabled in the application (`prepared_statement_cache_size=0` auto-detected in `db.py`).
- **FastAPI + SQLAlchemy 2.0 async** — typed Python web layer. Repositories isolate SQL, routers stay thin, Pydantic v2 schemas double as the OpenAPI source for hey-api TS codegen.
- **Martin v0.16** — vector tile server. Three SQL function sources (custom filtering, density join, zoom-gated). Direct DB connection (session mode on port 5432), not via pgbouncer.
- **Caddy 2.8** — single port (8080) reverse proxy. Unifies API + tiles + OpenAPI doc under one origin, simple frontend integration (no CORS).
- **hey-api 0.97** — generates TypeScript client from FastAPI's OpenAPI spec. Every endpoint is a typed function in `web/lib/api/sdk.gen.ts`.

---

## 4. Repository structure

```text
paczkomat-atlas/
├── api/                       FastAPI app + ingest pipeline
│   ├── alembic/               schema migrations (append-only)
│   ├── src/paczkomat_atlas_api/
│   │   ├── config.py          pydantic-settings, env vars
│   │   ├── db.py              async engine, SRID constants, pgbouncer detection
│   │   ├── logging.py         structlog config (TTY pretty / file JSON)
│   │   ├── main.py            app factory, router include
│   │   ├── middleware/        CacheControl + RequestLogging
│   │   ├── models/            SQLAlchemy 2.0 declarative
│   │   ├── repositories/      all SQL lives here, never in routers
│   │   ├── routers/           health, kpi, density, lockers, h3, velocity
│   │   ├── schemas/           Pydantic v2 request/response envelopes
│   │   └── ingest/            InPost client, PRG/BDL/Eurostat loaders, sync
│   └── tests/                 pytest, mostly smoke tests
├── web/                       Next.js scaffold (frontend lives here Phase 8)
│   ├── app/                   App Router pages (currently scaffold)
│   ├── components/            (empty, ready for FE work)
│   ├── lib/api/               hey-api generated TS client
│   ├── scripts/               codegen smoke script
│   └── openapi-ts.config.ts   hey-api config (input http://localhost:8080/openapi.json)
├── infra/
│   ├── compose/               docker-compose.yml + caddy/Caddyfile + db/init/
│   └── terraform/             Hetzner Cloud (Phase 9, placeholder)
├── data/                      gitignored — raw PRG shapefile, Eurostat geojson, GUS JSON
├── docs/                      ARCHITECTURE, DATA_MODEL, DEPLOY, walkthrough, recon/
├── scripts/                   ogr.sh, download_static_data.sh, codegen helpers
├── .claude/                   rules, agents, skills, hooks, MCP servers
├── .github/workflows/         ci.yml (ruff + mypy + pytest + codegen drift)
└── CLAUDE.md                  primary context entry point
```

- `api/` — backend code. Single Python package under `src/`.
- `web/` — Next.js 16, Tailwind 4, shadcn/ui, MapLibre. Currently has scaffold + generated TS client. Real UI work happens in Phase 8.
- `infra/` — single-host docker-compose for dev and production deploy. Caddy Caddyfile, db init SQL, GDAL container wrapper.
- `data/` — never committed. Raw downloads from PRG/Eurostat/GUS land here. Mounted into the api container for ingest.
- `docs/` — narrative documentation. `walkthrough.md` is the live tour, `recon/` is historical investigation reports (Nordic status, etc.), this file is the briefing.
- `scripts/` — bash entry points for static data downloads and the GDAL ogr2ogr wrapper.
- `.claude/` — rules files, subagent definitions, skills, hooks. Read by Claude Code every session.

---

## 5. The full database state — live

### 5.1 Containers

```text
SERVICE     STATE     HEALTH    PORTS
api         running   healthy   0.0.0.0:8000->8000/tcp
caddy       running             0.0.0.0:8080->8080/tcp
db          running   healthy   0.0.0.0:5432->5432/tcp
martin      running   healthy   0.0.0.0:3001->3000/tcp
pgbouncer   running   healthy   0.0.0.0:6432->5432/tcp
```

Five services, all healthy. Caddy fronts at `:8080`; direct ports on the other services for diagnostic use.

### 5.2 Extensions

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

Nine extensions. PostGIS + raster + topology for spatial; h3 + h3_postgis for hex indexing; TimescaleDB for the snapshots hypertable; pg_cron for scheduled MV refreshes; pg_stat_statements for query observability.

### 5.3 Tables, views, hypertable, cron jobs

**Tables (public schema):**

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
 public   | spatial_ref_sys  | table   (PostGIS internal — filtered by Alembic include_object)
```

**Materialized views:**

```text
   matviewname    | hasindexes
------------------+------------
 mv_country_kpi   | t
 mv_density_gmina | t
 mv_density_nuts2 | t
 mv_h3_density_r8 | t
```

All four have unique indexes — required for `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

**TimescaleDB hypertable:**

```text
 hypertable_name  | num_chunks | compression_enabled
------------------+------------+---------------------
 ingest_snapshots |          1 | t
```

`30d` chunk interval, compression after 14 days, drop after 730 days (2 years retention).

**pg_cron schedule:**

```text
  schedule  |                         command                         |          jobname
------------+---------------------------------------------------------+----------------------------
 15 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_country_kpi   | paczkomat_mv_country_kpi
 20 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_gmina | paczkomat_mv_density_gmina
 25 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_density_nuts2 | paczkomat_mv_density_nuts2
 30 4 * * * | REFRESH MATERIALIZED VIEW CONCURRENTLY mv_h3_density_r8 | paczkomat_mv_h3_density_r8
 45 4 * * * | ANALYZE lockers                                         | paczkomat_analyze_lockers
```

5-minute gaps to avoid lock contention. Cluster timezone Europe/Warsaw.

### 5.4 Row counts per table

```text
        t         | count
------------------+--------
 nuts2            |    299
 population_nuts2 |    291
 gminy            |   2477
 population_gmina |   2422
 lockers          | 150599
 ingest_snapshots | 336027
```

- **2,477** PL gminy from PRG (2022-06-27 vintage)
- **2,422** with population rows → **99.96%** match rate against GUS BDL (1 unmatched: parenthesized name; ignored)
- **299** NUTS-2 polygons from Eurostat 2024
- **291** with population rows (8 missing are non-EU regions or special territories)
- **150,599** lockers across all 14 markets, all statuses, ingested directly from the public InPost API
- **336,027** snapshot rows in the TimescaleDB hypertable

### 5.5 Index summary (33 indexes)

```text
    tablename     |            indexname
------------------+----------------------------------
 alembic_version  | alembic_version_pkc
 gminy            | gminy_pkey                       (teryt PK)
 gminy            | idx_gminy_geom                   (GIST, GeoAlchemy2)
 ingest_snapshots | idx_ingest_snapshots_geom        (GIST)
 ingest_snapshots | ingest_snapshots_snapshot_at_idx (TimescaleDB)
 ingest_snapshots | pk_ingest_snapshots
 lockers          | idx_lockers_geom                 (GIST, geography)
 lockers          | ix_lockers_content_hash          (change detection)
 lockers          | ix_lockers_country
 lockers          | ix_lockers_country_is_locker     (composite)
 lockers          | ix_lockers_country_status        (composite)
 lockers          | ix_lockers_gmina_teryt           (FK)
 lockers          | ix_lockers_h3_r6                 (h3 r6 ~36 km²)
 lockers          | ix_lockers_h3_r8                 (h3 r8 ~0.7 km²)
 lockers          | ix_lockers_is_locker
 lockers          | ix_lockers_name                  (unique)
 lockers          | ix_lockers_nuts2_id              (FK)
 lockers          | ix_lockers_status
 lockers          | lockers_pkey                     (id PK)
 mv_country_kpi   | ux_mv_country_kpi_country        (unique for REFRESH CONCURRENTLY)
 mv_density_gmina | ix_mv_density_gmina_per_10k      (ORDER BY)
 mv_density_gmina | ux_mv_density_gmina_teryt        (unique)
 mv_density_nuts2 | ix_mv_density_nuts2_country
 mv_density_nuts2 | ux_mv_density_nuts2_code         (unique)
 mv_h3_density_r8 | ix_mv_h3_density_r8_country
 mv_h3_density_r8 | ix_mv_h3_density_r8_geom         (GIST)
 mv_h3_density_r8 | ux_mv_h3_density_r8              (composite unique)
 nuts2            | idx_nuts2_geom                   (GIST)
 nuts2            | ix_nuts2_country
 nuts2            | nuts2_pkey                       (code PK)
 population_gmina | pk_population_gmina              (teryt, year)
 population_nuts2 | pk_population_nuts2              (code, year)
 spatial_ref_sys  | spatial_ref_sys_pkey
```

Spatial GIST indexes on all geom columns. Composite indexes for the known filter combinations (`country, is_locker`, `country, status`). Content hash index for fast change detection during incremental sync.

---

## 6. The data — every shape, every number, every gotcha

### 6.1 Per-country breakdown — the master table

```text
 country | total | lockers | pudo  | operating | created | disabled | open_247 | pct_247
---------+-------+---------+-------+-----------+---------+----------+----------+---------
 PL      | 33379 |   32853 |   526 |     32183 |    1025 |      171 |    29574 |    88.6
 FR      | 26577 |   11959 | 14618 |     17582 |    1584 |     7405 |     8930 |    33.6
 GB      | 24218 |   15065 |  9153 |     18403 |     702 |     5113 |    16398 |    67.7
 DE      | 17460 |       0 | 17460 |     17179 |       0 |      281 |      482 |     2.8
 ES      | 14700 |    4286 | 10414 |     10954 |     309 |     3437 |     2260 |    15.4
 IT      | 11120 |    5848 |  5272 |      9948 |    1004 |      168 |     4361 |    39.2
 AT      |  4785 |    1654 |  3131 |      3277 |       0 |     1508 |     1324 |    27.7
 SE      |  4454 |       0 |  4454 |         0 |       0 |     4454 |        0 |     0.0
 PT      |  3191 |     492 |  2699 |      2321 |      31 |      839 |      296 |     9.3
 HU      |  2719 |    1283 |  1436 |      2719 |       0 |        0 |     1284 |    47.2
 DK      |  2375 |       0 |  2375 |         0 |       0 |     2375 |        0 |     0.0
 FI      |  2375 |       0 |  2375 |         0 |       0 |     2375 |        0 |     0.0
 BE      |  1796 |     562 |  1234 |      1388 |      66 |      341 |      490 |    27.3
 NL      |  1450 |      44 |  1406 |      1004 |      44 |      402 |       46 |     3.2
```

**Observations frontend should know:**

- PL is 33,379 records, 98% lockers, ~89% 24/7 (column shows total — count over all statuses).
- DE has 17,460 records, zero lockers — 100% PUDO via Mondial Relay acquisition.
- SE/DK/FI have 9,204 catalog records combined but zero Operating. All Disabled. Pre-launch.
- GB has the second-largest absolute machine count (15,065 lockers).
- Note: `pct_247` in this table is over total records; the API's `pct_247` is over Operating+Overloaded only (88.5% PL vs 88.6% raw — small but real difference).

### 6.2 Physical type distribution per country

```text
 country |  physical_type  | count
---------+-----------------+-------
 AT      | legacy          |  1654
 BE      | newfm           |   551
 BE      | legacy          |    12
 ES      | newfm           |  4163
 ES      | bloqit          |   280
 ES      | legacy          |    15
 FR      | newfm           | 10440
 FR      | bloqit          |  1432
 FR      | legacy          |    88
 GB      | newfm           | 12977
 GB      | bloqit          |  1194
 GB      | legacy          |   439
 GB      | modular         |   396
 GB      | classic         |    59
 HU      | legacy          |  1283
 IT      | newfm           |  5347
 IT      | modular         |   259
 IT      | bloqit          |   243
 NL      | newfm           |    44
 PL      | newfm           | 18579
 PL      | screenless      |  5884
 PL      | modular         |  2621
 PL      | next            |  2452
 PL      | classic         |   683
 PL      | legacy          |    33
 PL      | bankopaczkomaty |    30
 PT      | newfm           |   505
 PT      | legacy          |     9
```

**Key findings:**

- **`newfm`** is the modern InPost machine — dominant everywhere active.
- **`bloqit`** is a partner-hardware family used in GB/FR/ES/IT.
- **`bankopaczkomaty`** is the PL-only PKO BP banking partnership (30 units).
- **`legacy`** appears in many markets — older hardware kept for catalog continuity. AT and HU are 100% legacy (no modern machines deployed yet).
- **`screenless`** is PL-only (5,884), a deliberately stripped-down variant.
- **`next`** and **`modular`** are newer iterations, mostly PL.

DE/NL have no `physical_type` for lockers because they have no lockers (the column is null for PUDO).

### 6.3 Density — the headline metric

#### Top 15 PL gminy

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

#### Top 15 EU NUTS-2

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

All 15 Polish. **Lubelskie at #15 still beats Budapest at #16.** The 16th PL voivodeship (Mazowieckie regionalny at 7.43) is still well above any non-PL.

#### Top 5 non-PL NUTS-2 — the comparison set

```text
   name_latn   | country | n_lockers | population | lockers_per_10k
---------------+---------+-----------+------------+-----------------
 Budapest      | HU      |       378 |    1686222 |            2.24
 Midi-Pyrénées | FR      |       697 |    3189432 |            2.19
 Aquitaine     | FR      |       743 |    3609164 |            2.06
 Limousin      | FR      |       148 |     729585 |            2.03
 Salzburg      | AT      |       115 |     571479 |            2.01
```

Five regions in three non-PL countries, all clustered around 2.0-2.24. Budapest (HU) is the densest non-PL EU region at **2.24 lockers per 10k**. Polish Wielkopolskie at **10.06** is **4.49× higher**.

#### Range and distribution

```text
 min_val | p25  | median | p75  | p95  | max_val |  n
---------+------+--------+------+------+---------+-----
    0.00 | 0.00 |   0.00 | 0.86 | 7.51 |   10.06 | 291
```

**Choropleth color scale recommendation:** quantile, 5 buckets at `[0, 0.5, 1, 2, 5, 10+]`. The median is 0 (most regions have effectively no lockers), p75 is 0.86, p95 is 7.51 — virtually all PL voivodeships hit the top bucket. Linear scales would wash everything into the bottom band.

Use the `--map-0` through `--map-5` choropleth ramp tokens (see Section 13).

### 6.4 Country KPI matrix (live API)

```json
{
  "data": [
    {"country":"PL","n_lockers":31687,"n_pudo":496,"n_total":32183,"n_247":28494,"pct_247":88.5},
    {"country":"GB","n_lockers":14388,"n_pudo":4015,"n_total":18403,"n_247":13265,"pct_247":72.1},
    {"country":"FR","n_lockers":10423,"n_pudo":7165,"n_total":17588,"n_247":7942,"pct_247":45.2},
    {"country":"DE","n_lockers":0,"n_pudo":17179,"n_total":17179,"n_247":472,"pct_247":2.7},
    {"country":"ES","n_lockers":4249,"n_pudo":6705,"n_total":10954,"n_247":2155,"pct_247":19.7},
    {"country":"IT","n_lockers":5097,"n_pudo":4851,"n_total":9948,"n_247":3823,"pct_247":38.4},
    {"country":"AT","n_lockers":1619,"n_pudo":1658,"n_total":3277,"n_247":1290,"pct_247":39.4},
    {"country":"HU","n_lockers":1283,"n_pudo":1436,"n_total":2719,"n_247":1284,"pct_247":47.2},
    {"country":"PT","n_lockers":486,"n_pudo":1835,"n_total":2321,"n_247":289,"pct_247":12.5},
    {"country":"BE","n_lockers":512,"n_pudo":877,"n_total":1389,"n_247":435,"pct_247":31.3},
    {"country":"NL","n_lockers":27,"n_pudo":977,"n_total":1004,"n_247":26,"pct_247":2.6},
    {"country":"FI","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null},
    {"country":"SE","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null},
    {"country":"DK","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null}
  ],
  "meta": {"count": 14}
}
```

**pct_247** here is over **operational** records only (Operating+Overloaded), not all records. PL 88.5%, GB 72.1%, FR 45.2%, DE 2.7% — the dashboard's real differentiator.

### 6.5 Velocity timeline (live API)

```json
{
  "data": [
    {"country":"PL","date":"2022-12-31","n_lockers":19215,"source":"press_release"},
    {"country":"PL","date":"2023-06-30","n_lockers":21840,"source":"press_release"},
    {"country":"PL","date":"2023-12-31","n_lockers":22870,"source":"press_release"},
    {"country":"PL","date":"2024-06-30","n_lockers":24120,"source":"press_release"},
    {"country":"PL","date":"2024-12-31","n_lockers":25440,"source":"press_release"},
    {"country":"PL","date":"2025-06-30","n_lockers":26500,"source":"press_release"},
    {"country":"FR","date":"2023-06-30","n_lockers":2200,"source":"press_release"},
    {"country":"FR","date":"2023-12-31","n_lockers":4500,"source":"press_release"},
    {"country":"FR","date":"2024-06-30","n_lockers":7800,"source":"press_release"},
    {"country":"FR","date":"2024-12-31","n_lockers":10100,"source":"press_release"},
    {"country":"FR","date":"2025-06-30","n_lockers":11400,"source":"press_release"},
    {"country":"GB","date":"2023-12-31","n_lockers":8200,"source":"press_release"},
    {"country":"GB","date":"2024-06-30","n_lockers":11500,"source":"press_release"},
    {"country":"GB","date":"2024-12-31","n_lockers":13800,"source":"press_release"},
    {"country":"GB","date":"2025-06-30","n_lockers":14700,"source":"press_release"},
    {"country":"IT","date":"2023-12-31","n_lockers":2400,"source":"press_release"},
    {"country":"IT","date":"2024-12-31","n_lockers":4900,"source":"press_release"},
    {"country":"IT","date":"2025-06-30","n_lockers":5700,"source":"press_release"},
    {"country":"ES","date":"2023-12-31","n_lockers":1800,"source":"press_release"},
    {"country":"ES","date":"2024-12-31","n_lockers":3600,"source":"press_release"},
    {"country":"ES","date":"2025-06-30","n_lockers":4200,"source":"press_release"}
  ],
  "meta": {"count": 21, "note": "Historical data from InPost press releases; daily live snapshots from 2026-05"}
}
```

**Growth multiples 2023-06-30 → 2025-06-30 (or earliest → latest):**

- PL: 19,215 → 26,500 = **+38%** in 30 months
- FR: 2,200 → 11,400 = **5.2×** in 24 months (fastest)
- GB: 8,200 → 14,700 = **+79%** in 18 months
- IT: 2,400 → 5,700 = **2.4×** in 18 months
- ES: 1,800 → 4,200 = **2.3×** in 18 months

**Source disclosure:** 21 points from public InPost press releases (annual reports 2022-2025). README must disclose this. Future versions will read from TimescaleDB continuous aggregates of daily snapshots once we have ≥6 months of history.

---

## 7. API surface — every endpoint with example output

All endpoints are GET, all return the `{ data, meta, errors? }` envelope.

### 7.1 Health

`GET /api/v1/health`

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

`Cache-Control: no-store`. Returns `status: "degraded"` if any check fails.

### 7.2 Network summary

`GET /api/v1/kpi/summary`

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

Six numbers, pre-aggregated. Drives the hero strip.

### 7.3 Country KPIs

`GET /api/v1/kpi/countries` — returns the full 14-row matrix (Section 6.4).

`GET /api/v1/kpi/countries/{country}`

```bash
curl -s http://localhost:8080/api/v1/kpi/countries/PL
```

```json
{
  "data": {"country":"PL","n_lockers":31687,"n_pudo":496,"n_total":32183,"n_247":28494,"pct_247":88.5},
  "meta": {}
}
```

404 if country code not in the dataset.

### 7.4 Density gminy

`GET /api/v1/density/gminy`

Query params: `voivodeship` (str), `min_population` (int ≥0), `limit` (1-2500, default 500), `offset` (≥0)

```bash
curl -s "http://localhost:8080/api/v1/density/gminy?voivodeship=mazowieckie&limit=3"
```

```json
{
  "data": [
    {"teryt":"1417082","name":"Wiązowna","voivodeship":"mazowieckie","population":16276,"n_lockers":26,"n_pudo":0,"lockers_per_10k":15.97},
    {"teryt":"1420021","name":"Raciąż","voivodeship":"mazowieckie","population":3932,"n_lockers":6,"n_pudo":0,"lockers_per_10k":15.26},
    {"teryt":"1413092","name":"Wieczfnia Kościelna","voivodeship":"mazowieckie","population":3597,"n_lockers":5,"n_pudo":0,"lockers_per_10k":13.9}
  ],
  "meta": {"total": 314, "limit": 3, "offset": 0}
}
```

Mazowieckie has 314 gminy. Ordered by `lockers_per_10k DESC NULLS LAST`.

`GET /api/v1/density/gminy/top`

Query params: `limit` (1-100, default 15), `min_population` (default 5000), `min_lockers` (default 5)

```bash
curl -s "http://localhost:8080/api/v1/density/gminy/top?limit=5"
```

```json
{
  "data": [
    {"teryt":"3015012","name":"Kuślin","voivodeship":"wielkopolskie","lockers_per_10k":19.62,"n_lockers":10,"population":5098},
    {"teryt":"2405052","name":"Rudziniec","voivodeship":"śląskie","lockers_per_10k":17.59,"n_lockers":19,"population":10802},
    {"teryt":"3209042","name":"Manowo","voivodeship":"zachodniopomorskie","lockers_per_10k":17.58,"n_lockers":10,"population":5687},
    {"teryt":"3207043","name":"Międzyzdroje","voivodeship":"zachodniopomorskie","lockers_per_10k":16.79,"n_lockers":10,"population":5957},
    {"teryt":"3015063","name":"Zbąszyń","voivodeship":"wielkopolskie","lockers_per_10k":16.07,"n_lockers":22,"population":13689}
  ],
  "meta": {"count": 5}
}
```

### 7.5 Density NUTS-2

`GET /api/v1/density/nuts2`

Query params: `country` (2-letter), `min_population` (≥0), `limit` (1-500, default 500), `offset`

```bash
curl -s "http://localhost:8080/api/v1/density/nuts2?country=PL&limit=3"
```

```json
{
  "data": [
    {"code":"PL41","name_latn":"Wielkopolskie","country":"PL","population":3438504,"n_lockers":3460,"n_pudo":70,"lockers_per_10k":10.06},
    {"code":"PL43","name_latn":"Lubuskie","country":"PL","population":947784,"n_lockers":936,"n_pudo":13,"lockers_per_10k":9.88},
    {"code":"PL21","name_latn":"Małopolskie","country":"PL","population":3318985,"n_lockers":3141,"n_pudo":43,"lockers_per_10k":9.46}
  ],
  "meta": {"total": 17, "limit": 3, "offset": 0}
}
```

`GET /api/v1/density/nuts2/top` — same shape, see Section 6.3.

### 7.6 Lockers

`GET /api/v1/lockers`

Query params: `country` (2), `is_locker` (bool), `status` (str), `location_247` (bool), `limit` (1-1000, default 500), `offset`

```bash
curl -s "http://localhost:8080/api/v1/lockers?country=PL&is_locker=true&location_247=true&limit=2"
```

```json
{
  "data": [
    {"name":"ADA01M","country":"PL","status":"Operating","is_locker":true,"physical_type":"newfm","location_247":true,"latitude":51.73834,"longitude":22.26405},
    {"name":"ADA01N","country":"PL","status":"Operating","is_locker":true,"physical_type":"next","location_247":true,"latitude":51.7444,"longitude":22.25875}
  ],
  "meta": {"total": 29571, "limit": 2, "offset": 0}
}
```

PL + locker + 24/7 → 29,571 matches.

`GET /api/v1/lockers/{name}`

```bash
curl -s http://localhost:8080/api/v1/lockers/ADA01M
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

404 on unknown name. Detail includes spatial-join results (`gmina_teryt`, `nuts2_id`) and last-update timestamp.

### 7.7 H3 cells

`GET /api/v1/h3/cells`

Query params: `country` (2), `min_count` (≥1, default 1), `limit` (1-10000, default 5000)

```bash
curl -s "http://localhost:8080/api/v1/h3/cells?country=PL&limit=3"
```

```json
{
  "data": [
    {"h3":"881f53c939fffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13},
    {"h3":"881f5234b1fffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13},
    {"h3":"881f53c99dfffff","country":"PL","n_lockers":13,"n_pudo":0,"n_total":13}
  ],
  "meta": {"count": 3, "resolution": 8}
}
```

Resolution 8 (~0.7 km² hex). For map rendering, use the tile endpoint; this is for tabular inspection.

### 7.8 Velocity

`GET /api/v1/velocity`

Query params: `country` (2-letter, optional)

See Section 6.5 for the full payload.

### 7.9 OpenAPI surface — full inventory

```text
  GET  /                                        root
  GET  /api/v1/density/gminy                    listGminy
  GET  /api/v1/density/gminy/top                topGminy
  GET  /api/v1/density/nuts2                    listNuts2
  GET  /api/v1/density/nuts2/top                topNuts2
  GET  /api/v1/h3/cells                         listH3Cells
  GET  /api/v1/health                           healthCheck
  GET  /api/v1/kpi/countries                    listCountryKpis
  GET  /api/v1/kpi/countries/{country}          getCountryKpi
  GET  /api/v1/kpi/summary                      getNetworkSummary
  GET  /api/v1/lockers                          listLockers
  GET  /api/v1/lockers/{name}                   getLocker
  GET  /api/v1/velocity                         getVelocity
```

13 endpoints, every one with an explicit `operation_id` for clean TS codegen function names.

---

## 8. Vector tiles — Martin sources

### 8.1 Catalog

```bash
curl -s http://localhost:8080/catalog
```

```json
{
  "tiles": {
    "gminy_density_tiles": {"content_type":"application/x-protobuf","description":"public.gminy_density_tiles"},
    "nuts2_density_tiles": {"content_type":"application/x-protobuf","description":"public.nuts2_density_tiles"},
    "lockers_tiles":       {"content_type":"application/x-protobuf","description":"public.lockers_tiles"},
    "gminy":               {"content_type":"application/x-protobuf","description":"public.gminy.geom"},
    "gminy_prg":           {"content_type":"application/x-protobuf","description":"staging.gminy_prg.geom"},
    "nuts2":               {"content_type":"application/x-protobuf","description":"public.nuts2.geom"},
    "lockers":             {"content_type":"application/x-protobuf","description":"public.lockers.geom"},
    "ingest_snapshots":    {"content_type":"application/x-protobuf","description":"public.ingest_snapshots.geom"},
    "_hyper_5_1_chunk":    {"content_type":"application/x-protobuf","description":"_timescaledb_internal._hyper_5_1_chunk.geom"}
  },
  "sprites": {}, "fonts": {}, "styles": {}
}
```

**Use the three function-backed sources** (top of the list). The auto-discovered raw `.geom` table sources are for debugging — they have no density attributes.

### 8.2 Tile sources detailed

**`lockers_tiles(z, x, y, query_params)`**
- Layer name: `lockers`
- Geometry: points
- Filter: `status IN ('Operating', 'Overloaded')`
- Optional URL query params: `country` (2-letter), `is_locker` (bool)
- Properties per feature: `name`, `country`, `is_locker`, `location_247`, `physical_type`
- Recommended zoom: **8+** (below, points overlap badly)

**`nuts2_density_tiles(z, x, y, query_params)`**
- Layer name: `nuts2_density`
- Geometry: polygons
- Joins `nuts2` ⨝ `mv_density_nuts2`
- Properties: `code`, `name_latn`, `country`, `n_lockers`, `n_pudo`, `population`, `lockers_per_10k`
- Recommended zoom: **0-7**

**`gminy_density_tiles(z, x, y, query_params)`**
- Layer name: `gminy_density`
- Geometry: polygons
- Joins `gminy` ⨝ `mv_density_gmina`
- Properties: `teryt`, `name`, `voivodeship`, `n_lockers`, `n_pudo`, `population`, `lockers_per_10k`
- Gated to zoom **≥ 5** (returns NULL otherwise — too many polygons at continental zoom)

### 8.3 Tile size sanity check

```text
eu_z3.mvt  (nuts2_density at z=3, central EU):   335,673 bytes  ~ 328 KB
pl_z6.mvt  (gminy_density at z=6, central PL):   611,908 bytes  ~ 597 KB
waw_z11.mvt (lockers at z=11, Warsaw corner):      2,454 bytes  ~ 2.4 KB
```

All under Martin's default 1 MB tile budget. The PL z=6 tile is the heaviest typical case; tighter zoom limits or `max-feature-count` reduction would help if it becomes an issue.

---

## 9. Frontend TypeScript client

### 9.1 Generated function inventory

```text
healthCheck       /api/v1/health
getNetworkSummary /api/v1/kpi/summary
listCountryKpis   /api/v1/kpi/countries
getCountryKpi     /api/v1/kpi/countries/{country}
listGminy         /api/v1/density/gminy
topGminy          /api/v1/density/gminy/top
listNuts2         /api/v1/density/nuts2
topNuts2          /api/v1/density/nuts2/top
listLockers       /api/v1/lockers
getLocker         /api/v1/lockers/{name}
listH3Cells       /api/v1/h3/cells
getVelocity       /api/v1/velocity
root              /
```

### 9.2 Generated files

```text
web/lib/api/
├── client/        (hey-api fetch client implementation)
├── core/          (hey-api runtime helpers)
├── client.gen.ts        25 lines  - client config
├── index.ts            101 lines  - re-exports
├── schemas.gen.ts      945 lines  - OpenAPI schemas
├── sdk.gen.ts          237 lines  - the 13 endpoint functions
└── types.gen.ts        989 lines  - all request/response types
                      2,297 lines total
```

Path note: this is `web/lib/api/`, not `web/src/lib/api/` — the project uses Next.js without a `src/` directory.

### 9.3 Usage example

```typescript
import { client, getNetworkSummary, topNuts2, listLockers } from '@/lib/api/sdk.gen'

client.setConfig({ baseUrl: 'http://localhost:8080' })

const summary = await getNetworkSummary()
// summary.data.data is typed as NetworkSummary (autocompleted)

const topRegions = await topNuts2({ query: { limit: 15 } })
// topRegions.data.data is Nuts2TopList[]

const lockers = await listLockers({ query: { country: 'PL', is_locker: true, limit: 100 } })
// lockers.data.data is LockerSummary[], lockers.data.meta has total/limit/offset
```

The smoke script at `web/scripts/codegen-smoke.ts` runs an end-to-end sanity check on this surface.

---

## 10. Numbers that matter (frontend story values)

These are the **headline numbers** from the live backend. They should appear somewhere on the page — KPI cards, chart annotations, body copy, footnotes:

| Number | What | Source |
|---:|---|---|
| **150,599** | Total pickup points fetched from InPost API | Sum across all countries, all statuses |
| **116,965** | Operating network total (the active footprint) | `mv_country_kpi.n_total` sum |
| **69,771** | Operating parcel locker machines | `mv_country_kpi.n_lockers` sum |
| **47,194** | Operating PUDO partner shops | `mv_country_kpi.n_pudo` sum |
| **31,687** | Operating PL lockers (the dominance proof) | `mv_country_kpi WHERE country='PL'` |
| **28,494** | PL lockers open 24/7 | `mv_country_kpi.n_247 WHERE country='PL'` |
| **88.5%** | PL 24/7 accessibility | `mv_country_kpi.pct_247 WHERE country='PL'` |
| **10.06** | Wielkopolskie lockers per 10k | top NUTS-2 |
| **2.24** | Budapest — top non-PL NUTS-2 | best non-PL region |
| **4.5×** | PL denser than densest non-PL | ratio 10.06 / 2.24 = 4.49 |
| **19.62** | Top single gmina (Kuślin, Wielkopolskie) | top gmina |
| **99.96%** | PL gmina population coverage | BDL→TERYT match rate (2,476/2,477) |
| **2,477** | PL gminy in dataset | PRG row count |
| **299** | EU NUTS-2 regions | Eurostat 2024 |
| **14** | Country markets InPost catalogs | distinct countries in lockers |
| **11** | Country markets with operational records | distinct countries with status='Operating' |
| **336,027** | Snapshot rows in TimescaleDB hypertable | live count |

---

## 11. Edge cases the frontend MUST handle

### 11.1 GB excluded from NUTS-2 view

```bash
curl -s "http://localhost:8080/api/v1/density/nuts2?country=GB"
```

```json
{"data": [], "meta": {"total": 0, "limit": 500, "offset": 0}}
```

**Reason:** Eurostat dropped UK from GISCO post-Brexit. 24,218 GB lockers have `nuts2_id = NULL` and do not appear in `mv_density_nuts2`.

**Frontend handling:** when the user selects "EU choropleth", show a note overlay on the GB region: "UK excluded from regional view (Eurostat post-Brexit). See country KPI strip for GB totals." GB still appears in `/kpi/countries` with its 14,388 operating lockers.

### 11.2 Nordic countries are pre-launch

```bash
curl -s http://localhost:8080/api/v1/kpi/countries/SE
curl -s http://localhost:8080/api/v1/kpi/countries/DK
curl -s http://localhost:8080/api/v1/kpi/countries/FI
```

```json
{"data":{"country":"SE","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null},"meta":{}}
{"data":{"country":"DK","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null},"meta":{}}
{"data":{"country":"FI","n_lockers":0,"n_pudo":0,"n_total":0,"n_247":0,"pct_247":null},"meta":{}}
```

**Reason:** SE/DK/FI records exist in the source API but **all** are status `Disabled` with `partner_id=99` (Mondial Relay) and a populated `mondial_relay_id`. The entire Nordic footprint is the dormant catalog of the post-acquisition Mondial Relay network; no active InPost-branded points exist in these markets. See `docs/recon/05-nordic-status.md` for the investigation.

**Frontend handling:** show these countries with a "Pre-launch" or "Catalog only" badge. Do **not** render them as zero on the map — render with a special style (`--border-strong` outline, `--bg-surface-1` fill) and a tooltip explaining the situation. The legacy catalog can be surfaced separately if relevant.

### 11.3 Germany is 100% PUDO

```text
 country | lockers |  pudo
---------+---------+--------
 DE      |       0 |  17460
```

**Reason:** InPost entered Germany through the Mondial Relay acquisition. Native parcel locker machines not yet deployed. Real business insight, not a data error.

**Frontend handling:** in the country card grid, DE should show a contextual note: "Mondial Relay network — machines pending."

### 11.4 PRG vintage 2022-06-27

**Reason:** The PRG shapefile we ingested ships with a 2022 vintage of gmina boundaries. TERYT codes are stable; micro-boundary changes since 2022 don't affect 10k-resolution density math.

**Frontend handling:** README disclosure only. UI doesn't need to surface this unless the user clicks "Data sources".

### 11.5 Empty top-N returns []

```bash
curl -s "http://localhost:8080/api/v1/density/gminy/top?limit=5&min_lockers=99999"
```

```json
{"data": [], "meta": {"count": 0}}
```

**Frontend handling:** show "No results match the current filter — try lowering thresholds" placeholder. Never blow up on empty arrays.

### 11.6 Slow first paint risk

The full `/lockers?country=PL&limit=1000` payload is ~150 KB JSON for 1000 rows. The map should **never** fetch this for rendering — it should use the tile endpoint. The JSON list endpoint is for tabular views only (top-N, filter table, detail).

### 11.7 Status enum drift

Statuses currently observed: `Operating`, `Created`, `Disabled`. Future API versions may add `Overloaded`, `NonOperating`, or new values. The MVs filter to `Operating + Overloaded` — defensive against future enum drift. Frontend should not hardcode the status list; pull from `/kpi/countries` (which already includes the filtered view) and treat unknowns as "unknown".

---

## 12. Performance characteristics

### 12.1 Endpoint latency (local, warm cache)

```text
/api/v1/kpi/summary                                  7 ms
/api/v1/kpi/countries                                7 ms
/api/v1/density/nuts2/top?limit=15                   6 ms
/api/v1/density/gminy/top?limit=15                   6 ms
/api/v1/h3/cells?country=PL&limit=100               10 ms
```

All endpoints under 15 ms. MV-backed reads are sub-10 ms. The h3 endpoint scans more rows so it's slightly slower.

### 12.2 Cache strategy

`CacheControlMiddleware` sets `public, max-age=3600, stale-while-revalidate=86400` on all GET endpoints under `/api/v1/density`, `/api/v1/kpi`, `/api/v1/h3`, `/api/v1/velocity`. Data refreshes daily at 04:15-04:45 Europe/Warsaw via pg_cron, so 1h max-age is conservative.

`/api/v1/health` is `Cache-Control: no-store`.

`/api/v1/lockers/*` returns `private, max-age=60` — list responses can stale-cache but per-locker details vary on filter combos.

### 12.3 Tile cache

Martin emits its own `Cache-Control: max-age=86400` on successful tile responses. Vector tiles are immutable per coordinate during the day — Cloudflare or any CDN in front of Caddy would dramatically reduce backend load in production.

### 12.4 Recommended SWR refresh intervals (frontend)

- `getNetworkSummary` — 5 min (rarely changes, daily MV refresh anyway)
- `listCountryKpis` — 5 min
- `topGminy` / `topNuts2` — 5 min
- `listLockers` (filtered) — 1 min, or on-demand via filter change only
- `healthCheck` — 30 s (status indicator)
- Velocity — no refresh, static for v1

---

## 13. Design system constraints

From `.claude/rules/design-tokens.md` (authoritative — never deviate):

### 13.1 Tokens

```css
/* Surfaces (warm-neutral, four-step elevation) */
--bg-canvas:    #0A0A0B
--bg-surface-1: #111113
--bg-surface-2: #18181B
--bg-surface-3: #1F1F23
--bg-inset:     #08080A

/* Borders (hairline) */
--border-subtle:  #1F1F23
--border-default: #27272A
--border-strong:  #3F3F46

/* Text (warm ivory — never pure white) */
--fg-default:  #EDEDEE
--fg-muted:    #A1A1A6
--fg-subtle:   #6B6B70
--fg-disabled: #3F3F46

/* Accent (dialed-down InPost yellow) */
--accent:    #E0A82E
--accent-hi: #F5C04E
--accent-lo: #6B4F14
--accent-fg: #0A0A0B

/* Semantic */
--success: #34D399
--warning: #FBBF24
--danger:  #F87171
--info:    #60A5FA

/* Choropleth (single-hue sequential amber) */
--map-0: #1A1A1F   /* zero / unknown */
--map-1: #2A2F1E   /* lowest bucket */
--map-2: #524018
--map-3: #8B6914
--map-4: #C29612
--map-5: #F5C04E   /* top bucket */

/* Typography */
--font-sans: var(--font-geist-sans)
--font-mono: var(--font-geist-mono)
```

### 13.2 Locked decisions

- **Theme:** dark, warm-neutral zinc surfaces, single amber accent. No light mode for v1.
- **Type:** Geist Sans + Geist Mono (via `next/font/google` in `app/layout.tsx`).
- **Colors:** all hex values defined above. NEVER introduce a new hex literal. Reference via `var(--token)`.
- **Map basemap:** self-hosted Protomaps PMTiles on Cloudflare R2 (planned), or open MapTiler dark-matter style as fallback for dev.
- **Choropleth ramp:** `--map-0` through `--map-5` for the 5-bucket quantile scale defined in Section 6.3.
- **Border radius:** max `rounded-md` (6px) on cards/inputs, `rounded-lg` (8px) on modals/popovers. NEVER `rounded-xl`+ on data UI.
- **Shadows:** none on cards. Hairline borders only.
- **Mono digits:** `tabular-nums` (or `font-mono`) for any numeric value — KPIs, table cells, axis labels.
- **Chart gridlines:** no vertical gridlines on bar/line charts. Horizontal only, `--border-subtle`.
- **Map hover:** use MapLibre `feature-state`, never re-render the layer.

### 13.3 Forbidden

- `#FFFFFF` / `bg-white` / `text-white`
- `#000000` / `bg-black` / `text-black`
- Any hex not in the tokens file
- Tailwind color classes that bypass tokens (`bg-zinc-900`, `text-amber-500`, etc.)
- `box-shadow` on cards
- Emojis in UI (allowed only if Niki explicitly asks)
- Inline `style={{}}` — use Tailwind utilities + CSS vars

---

## 14. Frontend rendering plan

Single-page dashboard, dark theme. Above-the-fold accessible on a 1440×900 viewport.

### 14.1 Layout sketch

```text
┌────────────────────────────────────────────────────────────┐
│ Top nav: "Paczkomat Atlas"      [PL | EU]   [GitHub] [docs]│
├────────────────────────────────────────────────────────────┤
│                                                            │
│  HERO STRIP (3 large KPI cards in a row):                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 116,965     │  │ 31,687      │  │ 4.5×        │         │
│  │ pickup pts  │  │ PL lockers  │  │ vs densest  │         │
│  │ across 11   │  │ 88.5% 24/7  │  │ non-PL EU   │         │
│  │ countries   │  │             │  │ region      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                            │
├────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┐  ┌──────────────────────┐│
│  │                              │  │  TOP 15 NUTS-2 BAR   ││
│  │                              │  │  All 15 PL bars in   ││
│  │       MAP (choropleth)       │  │  --accent. Annotation││
│  │   NUTS-2 default, toggle to  │  │  line at 2.24        ││
│  │   gminy when zoomed in       │  │  "Budapest, densest  ││
│  │                              │  │  non-PL region"      ││
│  │   [filter chips below map]   │  │  ─────────────────   ││
│  └──────────────────────────────┘  └──────────────────────┘│
│                                                            │
├────────────────────────────────────────────────────────────┤
│  COUNTRY MIX GRID — 11 cards in 4 cols × 3 rows            │
│  Each card: locker vs PUDO split bar + 24/7%               │
│  DE card has note: "Mondial Relay — machines pending"      │
│  SE/DK/FI hidden or rendered as "Pre-launch markets"       │
├────────────────────────────────────────────────────────────┤
│  EXPANSION TIMELINE                                        │
│  Line chart, 5 countries (PL/FR/GB/IT/ES) 2022-2025        │
│  Annotated growth multiples on the right edge per line     │
├────────────────────────────────────────────────────────────┤
│  PL DEEP-DIVE TABLE                                        │
│  Sortable gminy list (default: by density desc)            │
│  Filters: voivodeship dropdown, min population slider      │
└────────────────────────────────────────────────────────────┘
                                                              
┌────────────────────────────────────────────────────────────┐
│ Footer: data sources, limitations, repo link, deploy date  │
└────────────────────────────────────────────────────────────┘
```

### 14.2 Recommended chart library choices

- **KPI cards:** plain HTML + Tailwind, no library
- **Map:** MapLibre GL JS 5.x, vector tiles from Martin (Section 8)
- **Bar / line charts:** Recharts via `shadcn add chart` (already in dep allowlist)
- **KPI sparklines:** Tremor v3 (already in dep allowlist) — KPI only, not for general charts
- **Tables:** TanStack Table v8 + shadcn/ui Table primitives
- **Filters:** shadcn/ui Select, Combobox, Slider
- **Data fetching:** SWR (already in dep allowlist)

### 14.3 Frontend file structure (recommended)

```text
web/
├─ app/
│  ├─ layout.tsx          # Global layout, Geist fonts, theme
│  ├─ page.tsx            # The dashboard (single page for v1)
│  └─ globals.css         # Design tokens import
├─ components/
│  ├─ kpi-strip.tsx
│  ├─ density-map.tsx       # MapLibre wrapper, vector tile source
│  ├─ density-bar-chart.tsx # Top 15 NUTS-2 horizontal bars
│  ├─ country-mix-grid.tsx  # 11 country cards
│  ├─ velocity-timeline.tsx # 5-country line chart
│  └─ gminy-table.tsx       # Sortable, filterable PL gminy table
├─ lib/
│  ├─ api/                  # hey-api generated client (already here)
│  ├─ formatting.ts         # number formatters (Intl, mono digits)
│  └─ palettes.ts           # MapLibre paint expressions referencing tokens
└─ public/
   └─ basemap.json          # Protomaps PMTiles style ref (dev)
```

---

## 15. Known limitations to surface in UI footer / README

- **GB excluded from NUTS-2 view** (Brexit/Eurostat). 24k GB lockers still appear in country KPIs.
- **SE/DK/FI pre-launch markets** (Mondial Relay catalog, no operational records).
- **DE 100% PUDO** (Mondial Relay acquisition, native machines pending).
- **PRG boundary vintage 2022-06-27** (TERYT codes stable, micro-changes don't affect 10k-resolution math).
- **Velocity timeline static** from public InPost press releases for v1; daily snapshots accumulating in TimescaleDB hypertable for future continuous-aggregate views.
- **One PL gmina** (Słupia Jędrzejowska — 0.04% of PL records) unmatched in BDL due to parenthesized name; ignored.
- **Procrastinate job queue** planned but deferred; v1 uses plain async CLI invoked by pg_cron.
- **Map basemap** is the MapTiler dark-matter fallback in dev; production swap to self-hosted Protomaps PMTiles on Cloudflare R2 is a Phase 9 task.

---

## 16. Deploy plan (Phase 9+)

- **Target:** Hetzner CX22 (~4€/month), Ubuntu 22.04, single-host docker-compose
- **DNS:** subdomain on Niki's existing domain
- **TLS:** Caddy automatic via Let's Encrypt
- **CD:** GitHub Actions SSH deploy on push to main
- **No Cloudflare / no CDN for v1** — Caddy handles compression; Postgres + Martin handle their own cache
- **Backups:** pg_dump nightly to Cloudflare R2 (free tier); 7-day retention
- **Monitoring:** structlog JSON logs to stdout → docker logs; basic uptime via UptimeRobot

---

## 17. Commit-rate so far

```text
f07a234 Merge pull request #12 from Niki-3D/docs/walkthrough
f8dd830 docs: backend walkthrough — full system showcase
ab9f9ec chore(web): re-sync hey-api codegen against root operation_id
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
ae628e0 test(api): smoke tests against live data — one per endpoint
85172b3 feat(api): wire routers, middleware, CORS into FastAPI app
0f0d640 feat(api): velocity endpoint with static InPost press release data points
e723108 feat(api): h3 cells endpoint for heatmap data
38b8013 feat(api): locker endpoints — filtered list + detail by name
26a1682 feat(api): density endpoints — gminy/nuts2 lists + top-N
aec6a63 feat(api): KPI endpoints — network summary and per-country
7d5571b feat(api): rich health endpoint with MV and hypertable freshness
30f0897 feat(api): cache-control and request-logging middleware
4710994 feat(api): repository layer — all SQL lives here, never in routers
9a33c75 feat(api): Pydantic v2 schemas for envelope, KPIs, density, lockers, h3, velocity
4202ec4 Merge pull request #8 from Niki-3D/feat/boundaries-population
29ecff1 feat(ingest): Eurostat NUTS-2 boundaries and population loaders
e346a55 fix(ingest): handle Polish diacritics + name-only fallback for city-on-powiat-rights
36ee3d4 feat(ingest): BDL population loader with PRG-driven name+hierarchy matching
053760f feat(ingest): PRG gminy loader via GDAL container
aedf818 feat(data): fetch GUS BDL gmina units for name+hierarchy matching
c7e30fa infra(data): replace jq with python helper for BDL pagination
0bf7090 infra(data): static data download script for PRG, Eurostat, GUS
c4e8d6c infra(data): add GDAL container wrapper for shapefile ingest
528671b Merge pull request #7 from Niki-3D/chore/nordic-status-check
4292df7 docs(recon): nordic markets status mystery + new physical_types
656b6f7 Merge pull request #6 from Niki-3D/feat/ingest-pipeline
fe6077a fix(db): mv_h3_density_r8 unique index must include country
8be6211 feat(ingest): sync pipeline with upsert, spatial joins, snapshot, MV refresh
8d5c652 feat(ingest): InPost API client with retries and cross-country filters
2758481 feat(api): structlog config with pretty TTY / JSON file rendering
```

**67 commits on main** through Phase 6.5 + walkthrough. ~9 feature branches merged via PR.

---

## End of briefing

Frontend Claude reads this end-to-end. After this doc, they should be able to start building without asking what to render — every decision is encoded above.

If a number in this document disagrees with what's in the running backend, the **backend wins**. Re-run the live commands in Section 6 and Section 11 against the current state before shipping the frontend.
