# Paczkomat Atlas — web/

Single-page dashboard on the InPost public network. Loads every number from
the live backend at `http://localhost:8080` via the typed hey-api SDK in
`lib/api/`. Backend stays the source of truth for KPIs, density rankings,
country composition, velocity, and the per-gmina deep dive; tiles come from
the Martin vector tile server alongside the API.

## Run

```bash
# Bring the backend up first (api, db, martin, caddy, pgbouncer)
docker compose -f ../infra/compose/docker-compose.yml --env-file ../.env up -d

# Then this app
pnpm dev
```

Open <http://localhost:3000>.

## Architecture

```
app/page.tsx (Server Component)
├── probeHealth() ────────────────► /api/v1/health
├── getNetworkSummary() ──────────► /api/v1/kpi/summary
├── listCountryKpis() ────────────► /api/v1/kpi/countries
├── topNuts2({limit: 15}) ────────► /api/v1/density/nuts2/top
├── getVelocity() ────────────────► /api/v1/velocity
└── listGminy({limit: 2500}) ─────► /api/v1/density/gminy

  ↓ props ↓

components/dashboard/
├── nav.tsx                 — sticky chrome, scope toggle, health pulse
├── hero-kpis.tsx           — three KPI cards (server-rendered markup)
├── density-map-island.tsx  — client island, dynamic-imports density-map
├── density-map.tsx         — MapLibre choropleth, Martin vector tiles
├── density-bars.tsx        — Top 15 NUTS-2 (server-rendered markup)
├── country-share.tsx       — locker + PUDO stacked bars, 11-cell grid
├── velocity-timeline.tsx   — Recharts multi-line, growth-multiple labels
├── gminy-table.tsx         — TanStack Table v8 with filters
└── footer.tsx              — data sources, caveats, links
```

Page is a Server Component that fans out the API calls serially (one at a
time) before rendering. Anything interactive — map, charts, table filters,
country-share hover — is split into client islands.

## Design tokens

The dashboard is dark-only, warm-neutral surfaces, single amber accent. All
colours, radii, fonts come from CSS custom properties on
`:root[data-theme="dark"]` in `app/globals.css`, lifted verbatim from
`.claude/rules/design-tokens.md`. No hex literals appear in component code.

Choropleth ramp is the thermal palette (`--map-0` deep purple → `--map-5`
saturated amber); the legend in the map overlay shows it explicitly.

## Tech notes

- **Server Components by default.** Only the map and the interactive
  panels (`country-share`, `velocity-timeline`, `gminy-table`,
  `density-map`, `nav`) are `"use client"`.
- **Map** uses MapLibre GL JS 5.x and connects to the backend's Martin
  function tile sources (`/tiles/nuts2_density_tiles`,
  `/tiles/gminy_density_tiles`). Hover state uses `feature-state` — the
  layer never re-renders per move.
- **Charts** use Recharts 3 (already in shadcn's chart wrapper space).
- **Table** uses TanStack Table v8 with custom filter UI (voivodeship
  multiselect, population slider, name search). All filtering happens
  client-side over the full 2.4k-row dataset.
- **Data fetching** in client islands could use SWR (configured in
  `lib/swr-provider.tsx`) but the dashboard is fully server-rendered
  for the initial paint, so SWR currently sits unused on the client.
- **API base URL** comes from `NEXT_PUBLIC_API_BASE_URL`, falling back
  to `http://localhost:8080`. `lib/api.ts` runs `client.setConfig()`
  at import time so every SDK call uses the right host.

## Known quirks

- The dev server occasionally pre-warms during HMR and the parallel-fetch
  pattern under that load used to tip the backend pool over. We
  intentionally fetch the six endpoints serially in page.tsx and fixed the
  underlying pre-ping incompatibility in `api/src/paczkomat_atlas_api/db.py`.
- Range/text inputs in the gminy filter trigger a benign hydration
  mismatch on Chromium (caret-color and background shorthands get added
  to the DOM before React hydrates). `suppressHydrationWarning` is set
  on those inputs.

## Scripts

```bash
pnpm dev               # dev server, port 3000
pnpm build             # production build
pnpm start             # serve production build
pnpm typecheck         # tsc --noEmit, must be clean
pnpm codegen           # regenerate lib/api from OpenAPI at :8080/openapi.json
pnpm codegen:check     # CI guard — fail if codegen diff is non-empty
```

## Screenshots

See `docs/screenshots/` in the repo root for the desktop and mobile
captures used in the PR.
