# Paczkomat Atlas — Claude Code Context

InPost parcel locker network analytics. Dual-granularity: Poland (gmina detail with GUS population) and EU (NUTS-2 overview with Eurostat). Built for the InPost Technology Internship 2026 submission.

## Stack

- **web/**: Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui · MapLibre GL JS 5 · Recharts v3 (via shadcn charts) · Tremor v3 (KPI cards only)
- **api/**: FastAPI 0.115+ · SQLAlchemy 2.0 async (asyncpg) · Polars · Pydantic v2 · uv-managed
- **db**: PostgreSQL 16 + PostGIS 3.5
- **tiles**: Protomaps PMTiles self-hosted (Cloudflare R2)
- **infra**: Docker Compose · Caddy · Hetzner CX22 · GitHub Actions deploy · Terraform

## Run

- Frontend dev: `cd web && pnpm dev` (:3000)
- Backend dev: `cd api && uv run fastapi dev` (:8000)
- Local stack: `docker compose -f infra/compose/docker-compose.yml up`
- Typecheck: `pnpm -w typecheck && cd api && uv run mypy .`
- Lint: `pnpm -w lint && cd api && uv run ruff check`
- Test: `pnpm -w test && cd api && uv run pytest`

## Design tokens

Source of truth: `.claude/rules/design-tokens.md`. Never introduce a new hex. Reference `var(--…)` CSS vars, not Tailwind color classes.

## Conventions

- Numbers render in `font-mono` with `tabular-nums`. Always.
- Cards: `rounded-md`, hairline border, no shadows. Shadows only on popovers/modals.
- Charts: shadcn `<ChartContainer>` + Recharts. No vertical gridlines.
- Map: separate `fill` and `line` layers, never `fill-outline-color`. `feature-state` for hover.
- PostGIS: store SRID 4326 (`geography(Point)`), use EPSG:2180 for distance ops in PL.
- Ingest: exclude `province IN ('test','TEST')` and `(lat,lon) = (0,0)`. See `.claude/rules/data-quality-rules.md`.
- Python: type hints everywhere, Polars not Pandas, `Decimal` where precision matters.
- TS: `strict: true`, no `any`, no default exports outside Next.js page/layout files.

## Workflow

1. Check `.claude/skills/` first for any new component, query, or layer.
2. Follow `.claude/rules/` for domain conventions.
3. Typecheck + lint before declaring done (PostToolUse hook enforces).
4. For research-heavy or boilerplate tasks, spawn the relevant subagent.

## Do not

- Add dependencies without justification.
- Edit shipped migrations — create new ones.
- Modify `docs/recon/` — read-only historical record.
- Commit `.env` or `*.local.json`.
- Use Pandas where Polars works.
