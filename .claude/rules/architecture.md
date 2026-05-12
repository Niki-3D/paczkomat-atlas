# Architecture

## Stack

| Layer | Tech | Role |
|---|---|---|
| Language (backend) | Python 3.12+ | API, ingest, workers |
| Language (frontend) | TypeScript strict | Dashboard, landing |
| API framework | FastAPI 0.115+ | Async REST |
| ORM | SQLAlchemy 2.0 async | asyncpg driver |
| Validation | Pydantic v2 | Schemas, config |
| Database | PostgreSQL 16 + PostGIS 3.5 | Lockers, boundaries, population |
| Data processing | Polars 1.0+ | Ingest transforms, aggregations |
| Frontend | Next.js 16 (App Router) | Dashboard + landing |
| Styling | Tailwind v4 + shadcn/ui | Dark theme, dense layout |
| Map | MapLibre GL JS 5 + PMTiles | Vector basemap + choropleth |
| Charts | Recharts v3 (via shadcn) + Tremor v3 (KPI) | Data viz |
| Deploy | Docker Compose + Caddy + Hetzner | Single VM, ~4€/mo |
| Tiles | Protomaps PMTiles on Cloudflare R2 | Self-hosted basemap |

## Repo structure

```
paczkomat-atlas/
├── api/                  # FastAPI app
│   └── src/paczkomat_atlas_api/
│       ├── main.py       # entrypoint, app factory
│       ├── config.py     # pydantic-settings
│       ├── db.py         # async engine, session factory
│       ├── models/       # SQLAlchemy models
│       ├── schemas/      # Pydantic request/response (create when needed)
│       ├── routers/      # FastAPI routers, one per domain
│       ├── ingest/       # InPost API client, GUS loader, PRG loader
│       └── exceptions.py # domain exceptions (create when needed)
├── web/                  # Next.js app
│   └── app/
│       ├── page.tsx      # / (landing)
│       └── app/          # /app/* (dashboard)
├── infra/
│   ├── compose/          # docker-compose.{yml,prod.yml} + Caddyfile
│   └── terraform/        # Hetzner Cloud provisioning
├── docs/                 # ARCHITECTURE.md, DATA_MODEL.md, DEPLOY.md, recon/
└── .claude/              # rules, agents, skills, hooks
```

## Module rules

REQUIRED:
- One FastAPI router per domain. `routers/health.py`, `routers/lockers.py`, etc.
- Ingest sources isolated: `ingest/inpost_client.py`, `ingest/bdl_client.py`, `ingest/prg_loader.py`. Never cross-import.
- `models/` = SQLAlchemy only. `schemas/` = Pydantic only. They never import each other.
- All external API clients use `httpx.AsyncClient` with timeout + retries.
- Decimal/datetime conversions happen at API boundaries, never inside business logic.

FORBIDDEN:
- Pandas anywhere (Polars instead).
- ORM `relationship()` lazy-loading in async code (always `selectinload` explicit).
- Importing from `routers/` into `ingest/` or `models/` (one-way: routers depend on services, not vice versa).
- Float for monetary values.
- Raw SQL strings outside `ingest/` and `migrations/` — use SQLAlchemy core or ORM.
- Hardcoded SRIDs in queries — constants in `db.py`.

## Data layer

```
InPost API ──▶ ingest/inpost_client.py ──▶ Postgres (lockers table)
GUS BDL    ──▶ ingest/bdl_client.py    ──▶ Postgres (population_gmina)
PRG SHP    ──▶ ingest/prg_loader.py    ──▶ Postgres (gminy table)
Eurostat   ──▶ ingest/eurostat_client.py ─▶ Postgres (nuts2, population_nuts2)
                                              ↓
                                      Materialized Views
                                       (mv_density_*)
                                              ↓
                                          FastAPI
                                              ↓
                                       Next.js dashboard
```

Detail in `docs/DATA_MODEL.md` (updated as schema lands).

## API conventions

- Base path: `/api/v1/`
- All responses: `{ "data": ..., "meta": { "total"?, "offset"?, "limit"? }, "errors"? }`
- Pagination: `?offset=0&limit=100` (max 500)
- Pydantic v2 for all request/response bodies
- Async handlers + async SQLAlchemy sessions
- Error envelope: `{ "errors": [{ "code": "...", "message": "...", "field"?: "..." }] }`
- No auth in v1 (public read-only dashboard data). Add later if needed.

## Frontend conventions

- App Router only. No pages router.
- Server Components default. `'use client'` only when needed (hooks, events, MapLibre).
- Data fetching: SWR with `refreshInterval` if live, plain server-side fetch if static.
- All API access through `web/lib/api.ts` — never raw `fetch()` in components.
- Types in `web/lib/types.ts` mirror Pydantic schemas exactly.

## Environment

- `.env` local dev (gitignored)
- `.env.example` committed, all vars documented
- `api/src/paczkomat_atlas_api/config.py` reads via pydantic-settings
- Docker services read `.env` via `env_file`

## Learned

<!-- Append findings here. Newest first. Format: `[YYYY-MM-DD] insight` -->
