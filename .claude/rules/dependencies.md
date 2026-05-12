# Dependencies

## Adding a dep

Before `pnpm add` or `uv add`, answer in the commit body:
1. **What** does it do?
2. **Why** can't existing deps + ~50 lines of code do it?
3. **Cost** — bundle size (frontend) / install time (backend) / maintenance burden?
4. **Alternatives** considered and rejected?

If you can't answer all four, don't add it.

## Backend (Python)

Already committed deps (don't re-justify):
- `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic`, `pydantic-settings` — stack core
- `polars` — data processing (Pandas-prohibited)
- `httpx` — HTTP client
- `structlog` — structured logging
- `alembic` — migrations
- `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov` — dev

Likely future adds (pre-approved, just install):
- `shapely` — geometry ops in Python (if PostGIS doesn't suffice)
- `geopandas` — only if shapely insufficient (heavy, prefer raw PostGIS)
- `tenacity` — retry decorator
- `aiocache` — Redis cache wrapper if/when Redis added

## Frontend (TypeScript)

Already committed deps (don't re-justify):
- `next`, `react`, `react-dom` — stack core
- `geist` — fonts
- `tailwindcss`, `@tailwindcss/postcss` — styling
- `shadcn` ecosystem (`@base-ui/react`, `class-variance-authority`, `tw-animate-css`, `clsx`, `tailwind-merge`)
- `lucide-react` — icons
- `maplibre-gl`, `pmtiles` — map
- TypeScript + types

Likely future adds:
- `swr` — data fetching
- `recharts` (via `shadcn add chart`) — charts
- `@tremor/react` — KPI sparklines ONLY (don't use for other charts)
- `zod` — runtime schema validation (only if needed beyond TS types)

## Forbidden

- `lodash` — modern JS / TS replaces it
- `moment` — use `date-fns` or native `Intl`
- `axios` — `fetch` + `httpx` are enough
- `pandas` — Polars only
- Any UI lib that ships its own design system (Material UI, Chakra, Mantine, Ant Design)
- Any state lib beyond SWR/React state until proven necessary (no Redux, Zustand, Jotai upfront)

## Version pinning

- Backend: pin majors in `pyproject.toml` via uv resolution.
- Frontend: caret ranges default (`^x.y.z`). pnpm lockfile committed.
- Bump deliberately, not opportunistically. Bump = its own commit: `chore(deps): bump <pkg> <from>→<to>`.
