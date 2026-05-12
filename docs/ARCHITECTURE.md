# Architecture

> Module breakdown for paczkomat-atlas. Living document.

## Topology

```
┌──────────────┐        ┌────────────────┐        ┌──────────────────┐
│  web (Next)  │ ─────▶ │  api (FastAPI) │ ─────▶ │  PostgreSQL +    │
│  MapLibre +  │  JSON  │  /v1/*         │  SQL   │  PostGIS         │
│  shadcn      │ ◀───── │                │ ◀───── │                  │
└──────────────┘        └────────────────┘        └──────────────────┘
       │                                                    ▲
       └─── PMTiles (R2 / CDN) ─────────────────────────────┘
                                                            │
                                          ┌─────────────────┴───────┐
                                          │  Ingest workers          │
                                          │  - InPost API daily      │
                                          │  - PRG / Eurostat geoms  │
                                          │  - GUS / Eurostat pop    │
                                          └──────────────────────────┘
```

## Modules

### web/
- `app/` — App Router. `/` landing, `/app` dashboard.
- `components/{ui,map,charts,landing}` — feature-grouped components.
- `lib/{api,types,utils,map/}` — client helpers.

### api/
- `src/paczkomat_atlas_api/`
  - `main.py` — FastAPI app + `/health`
  - `config.py` — pydantic-settings
  - `db.py` — async SQLAlchemy engine + session
  - `models/` — ORM models (lockers, gminy, nuts2, population)
  - `routers/` — REST endpoints (kpi, density, search, geo)
  - `ingest/` — InPost client, geo loaders (PRG, NUTS-2, GUS, Eurostat)
- `alembic/` — migrations
- `tests/` — pytest

### infra/
- `compose/` — Docker Compose for local + prod overlay
- `terraform/` — Hetzner Cloud provisioning

## Data flow

1. **Ingest** (cron, daily 02:00 UTC) → InPost API → Postgres `lockers` table.
2. **Materialize** → density MVs refresh after ingest.
3. **API** → reads from MVs for hot paths, raw tables for filters.
4. **Tiles** → choropleth polygons baked nightly to PMTiles in R2.
5. **Web** → fetches JSON KPI/table data via API + PMTiles directly from R2.

## TODO

- [ ] Caching layer (Redis or in-process LRU)
- [ ] Auth strategy (likely none — public read-only)
- [ ] Rate limiting at Caddy
