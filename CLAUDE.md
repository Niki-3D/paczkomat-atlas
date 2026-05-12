# Paczkomat Atlas — Claude Code Context

InPost parcel locker network analytics. Dual-granularity: Poland (gmina detail, GUS population) and EU (NUTS-2 overview, Eurostat). Built for the InPost Technology Internship 2026 submission.

## Quick facts

- **web/**: Next.js 16 (App Router) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui · MapLibre GL JS 5 · Recharts (via shadcn) · Tremor (KPI only)
- **api/**: FastAPI 0.115+ · SQLAlchemy 2.0 async (asyncpg) · Polars · Pydantic v2 · uv-managed
- **db**: PostgreSQL 16 + PostGIS 3.5
- **tiles**: Protomaps PMTiles self-hosted (Cloudflare R2)
- **infra**: Docker Compose · Caddy · Hetzner CX22 · GitHub Actions · Terraform

## Run

- Frontend: `cd web && pnpm dev` (:3000)
- Backend: `cd api && uv run fastapi dev` (:8000)
- Local stack: `docker compose -f infra/compose/docker-compose.yml up`
- Typecheck: `pnpm -w typecheck && cd api && uv run mypy .`
- Lint: `pnpm -w lint && cd api && uv run ruff check`
- Test: `pnpm -w test && cd api && uv run pytest`

## Rules — read the relevant file before working

| Rule file | When to read |
|---|---|
| `.claude/rules/architecture.md` | Adding modules, routers, ingest sources |
| `.claude/rules/code-quality.md` | Writing or reviewing any code |
| `.claude/rules/behavior.md` | Every session — how to act |
| `.claude/rules/git-conventions.md` | Every commit |
| `.claude/rules/testing.md` | Writing or reviewing tests |
| `.claude/rules/dependencies.md` | Before `pnpm add` or `uv add` |
| `.claude/rules/design-tokens.md` | Any UI/styling work |
| `.claude/rules/postgis-conventions.md` | Any spatial query or migration |
| `.claude/rules/data-quality-rules.md` | InPost API ingest |

## Skills (auto-invoke on description match)

`.claude/skills/`: `add-shadcn-component`, `add-recharts-chart`, `postgis-spatial-query`, `maplibre-layer`.

## Subagents (spawn for domain work)

`.claude/agents/`: `map-styler`, `chart-stylist`, `postgis-query-author`, `design-reviewer`.

## Workflow

1. Read relevant rules for the task.
2. Check skills/agents — invoke or spawn if applicable.
3. State assumptions + plan if non-trivial (per `behavior.md`).
4. Implement.
5. Typecheck + lint (PostToolUse hook enforces).
6. Commit per `git-conventions.md` — one logical change = one commit.
7. Update `## Learned` section of relevant rule file if you discovered something non-obvious.

## Hard nos

- No `.env` commits. No data files (`*.parquet`, `*.pmtiles`, `*.shp`).
- No Pandas (Polars only). No `any` in TS. No `print()` in API code (structlog).
- No new hex literals in components (CSS vars only).
- No bundling unrelated changes in one commit.
- No editing shipped Alembic migrations.
- No modifying `docs/recon/` — historical artifact.
