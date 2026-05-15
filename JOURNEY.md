# How Paczkomat Atlas was built

The brief was one sentence. "Do something interesting with our public locker API." What follows is the story of how that became a 150,000-record geospatial dashboard with a live deploy and a 99.96% data match rate.

The dashboard is the deliverable. This document is the meta-deliverable — how I narrow a vague task, make architectural decisions, and use AI as a force multiplier rather than a substitute for judgment.

## The brief

> "InPost has a public API exposing parcel locker locations. Do something interesting with it."

Intentional vagueness. The recruiter signaled this is about how you think, not what you build. There are dozens of valid interpretations: a route optimizer, a coverage-gap analyzer, a network health monitor, a competitor benchmark, a price simulator. The choice itself is part of the evaluation.

## How I narrowed it

I chose density per 10,000 inhabitants as the analytical lens. Reasons:

- It reframes "how many lockers" into "how well-served is each region" — a more interesting question than a count.
- It puts inhabitants and lockers in the same denominator, enabling fair cross-country comparison.
- It exposes the headline finding only after you do the math: the top 15 NUTS-2 regions in EU by locker density are all Polish voivodeships, and Wielkopolskie at 10.03 lockers per 10k is 4.5× denser than the densest non-PL region (Budapest at 2.24).

That headline became the anchor of the entire dashboard. Everything else — the three map modes, the country composition strip, the velocity timeline, the gminy deep-dive — supports or contextualizes it. If I had to cut to a single sentence and one number, that's what I'd ship.

## Phase 0 — research before code

Before writing any ingest module, I ran a four-country API audit (FR / GB / DE / IT) to verify that PL-shaped assumptions held cross-border. Findings that shaped the schema:

- **Italy marks test data via `name` field** (regex `^DGM.*TEST`), not via `province`. A naive PL filter would have silently included thousands of test rows in IT's count.
- **Germany returned 100% PUDO** in the page-1 sample — predicted (correctly) that DE has zero native parcel machines, only Mondial Relay partner shops from the 2021 acquisition. Live data confirms: 17,200 PUDO, 0 lockers in DE.
- **Sweden, Denmark, Finland**: every record `Created` or `Disabled`, none `Operating`. Pre-launch markets. The dashboard treats them as zero operational reach with a separate disclosure.
- **Two new status enum values not in PL**: `Overloaded` (treat as valid operational — FR-specific signal for "temporarily full") and `NonOperating` (default-exclude).

`.claude/rules/data-quality-rules.md` became cross-country aware before any code shipped. That saved hours of "why is the IT count weirdly high" debugging downstream.

## Architectural choices

### Why a single Postgres image

I picked `timescaledb-ha:pg16.6-ts2.17.2-all` over three separate database services. The image bundles TimescaleDB + PostGIS + h3 + pgvector + pg_stat_statements + pg_cron — one connection pool, one backup target, one observability surface. A spatial join joined to an h3 aggregation joined to a hypertable lookup all happens in a single SQL statement without cross-database federation. The trade-off is being locked to the image's h3 version (4.1.4), which is API-compatible with current h3 anyway. For a 4-day build with a single ops engineer, the consolidation easily wins.

### Why Martin for vector tiles

33,338 PL lockers + 299 NUTS-2 polygons + 2,477 gminy as raw GeoJSON is a noticeably laggy MapLibre experience. Martin pre-tiles server-side from three SQL functions (`lockers_tiles`, `nuts2_density_tiles`, `gminy_density_tiles`) marked `IMMUTABLE PARALLEL SAFE STRICT`. Postgres parallelizes the per-tile MVT generation; MapLibre fetches only the viewport tiles. The `gminy_density_tiles` function returns `NULL` for `z < 5` because at lower zooms a single tile would contain thousands of tiny polygons and blow Martin's default 1MB budget. Server-side gating is cheaper than client-side culling.

### Why pgbouncer in transaction-pooling mode

Async SQLAlchemy under HTTP burst hammers connection limits — every request a session, every session a connection. Transaction-mode pgbouncer caps at 25 concurrent DB connections regardless of how many requests are in flight. The complication: prepared statements are pooled per-session in asyncpg, so transaction-mode pooling needs `prepared_statement_cache_size=0`. `db.py` auto-detects this from `:6432` in the URL or `pgbouncer` in the hostname. A later discovery: `pool_pre_ping=True` doesn't work through transaction pooling (the pre-ping query may land on a different backend than the actual query), so I disabled that conditionally too.

### Why hey-api codegen

Hand-writing TS types for 13 endpoints across 6 Pydantic schemas is drift waiting to happen. hey-api generates client code from FastAPI's OpenAPI spec; a CI guard fails the build if regenerated files differ from committed ones. The one investment that made the codegen worth it was adding explicit `operation_id` on every FastAPI route — so the generated functions are `getNetworkSummary` and `listGminy` rather than the auto-derived `summary_api_v1_kpi_summary_get`. The frontend reads typed responses; refactoring an endpoint's payload shape triggers a typecheck failure on the calling component, not a 500 in production.

### What I chose not to build

Three deferred-explicitly items: **Procrastinate** (a job queue with retries and fan-out) was overkill for a single daily ingest CLI that pg_cron can drive in five lines. A **CDN** in front of Caddy would be premature optimization at expected traffic levels — gzip + cache-control headers cover the same ground. **PMTiles self-hosted on R2** is the right end-state for basemap independence, but OpenFreeMap is free, no-key, and competently maintained; the SPOF is documented and worth the cost for v1. Knowing what to skip is part of the engineering decision.

## The workflow

This is where AI use needs honest framing. **I planned the architecture, made the calls on every trade-off, reviewed every PR.** Claude Code did the implementation, applied conventions encoded in `.claude/rules/`, and ran the review agents I configured.

Specifically:

- **9 rule files** in `.claude/rules/` (architecture, code-quality, postgis-conventions, data-quality, git-conventions, design-tokens, dependencies, testing, behavior) encode project conventions: type hints everywhere, SRID constants over literals, GIST indexes on every geometry column, design tokens over hex literals, one logical change per commit. Claude Code reads them before writing code.
- **Three review agents** — `design-reviewer` (existed), `architecture-reviewer` (I added), `rules-compliance-reviewer` (I added).
- **18 PRs across 4 days**, each scoped to one phase. Branch off main, implement, review, merge.

The architecture-reviewer caught real issues I would have missed: a pgbouncer prepared-statement race documented as H1, a CI workflow with `pytest -q || echo "..."` that masked test failures (`|| echo` makes the step always succeed — fixed), a Martin URL hardcoded in a Next.js component (moved to env), and a deploy procedure that existed only in tribal knowledge until DEPLOY.md was written.

The rules-compliance-reviewer caught two ingest modules using SRID literal `4326` inline instead of the `SRID_WGS84` constant from `db.py`. Easy fix, the kind of thing that drifts when nobody is auditing.

This is not "AI built it." This is engineering judgment with AI as a force multiplier at the implementation layer.

## Engineering notes

Five vignettes — one each from research, data archaeology, visualization, deploy debugging, and the review process. There were more (the Turbopack cache, the GeoAlchemy2 double-index trap, the Martin tile cache, the heatmap blob problem, the asyncpg-SRID bind-type collision); these five give the best cross-section of what the build felt like.

### The 99.96% gmina match

GUS BDL returns 12-character internal IDs, not TERYT codes. The ID structure encodes TERYT but the decomposition is undocumented for edge cases. Three options: reverse-engineer the BDL ID format (high risk of silent miscoding), find a mapping file from GUS (endpoint unstable, vintage uncertain), or name-and-hierarchy match against PRG, which carries authoritative TERYT in `JPT_KOD_JE`. I picked option three. Initial implementation hit 99.8% match. Two refinements brought it to 99.96%: a Polish-aware diacritic translate table for `ł/ą/ć/ę/ń/ó/ś/ź/ż` (Python's `NFKD` doesn't decompose them — these are atomic Latin Extended-A code points), and a name-only fallback for `miasta na prawach powiatu` like Warszawa where the BDL hierarchy collapses two admin levels. Final: 2,476 of 2,477. The one miss is Słupia (Jędrzejowska) — the parenthesized name defeats whitespace-tolerant normalization. Real-world data archaeology beat reverse-engineering an undocumented ID scheme.

### The multi-language label stack

First basemap was CartoDB dark raster tiles. They look great until you zoom out and see the Baltic Sea labeled in five languages stacked vertically because each tile slice bakes the locale of whatever country it intersects. `Morze Bałtyckie / Itämeri / Östersjön / Mer du Nord / Балтийское море`. Switched to `dark_only_labels` — same problem, just labels without the basemap underneath. The realization: when the rendering pipeline bakes locale at upstream, the only fix is moving to a pipeline that defers that choice. Final solution: OpenFreeMap vector tiles (free, no API key, OpenMapTiles schema) with my own symbol-layer paint expressions reading `coalesce(name:en, name)`. Single language stack — English where available, native otherwise. Bonus: Noto Sans fonts from OpenFreeMap render Polish diacritics natively without font-fallback fallbacks.

### The NEXT_PUBLIC_ inlining trap

Deploy day. The page took 77 seconds per request. API calls were 200ms each in isolation. I'd already pointed the web container's `NEXT_PUBLIC_API_BASE_URL` env var at the internal `http://api:8000` hostname at container start time. Server-side fetches should stay on the docker network. They didn't. They went out through eth0, NAT'd back to the public IP, through Caddy, back to api:8000. Loopback hell. The root cause is in Next.js's build behavior, not the runtime: **NEXT_PUBLIC_* variables get inlined at build time into BOTH the client AND the server bundle.** Setting the env var at runtime did nothing — the bundled SDK had `http://62.238.7.125` hardcoded as a string literal. Fix: separate `INTERNAL_API_BASE_URL` env var, read by `web/lib/api.ts` only when `typeof window === "undefined"`. The client bundle still uses the inlined public URL. SSR drops from 77 seconds to 0.5. Mental-model lesson: build-time substitution is not run-time configuration.

### The data integrity catch

A pre-deploy review found four hardcoded values in the dashboard JSX: Budapest at 2.24, Wielkopolskie at 10.06, the 4.5× density ratio, and a "16th place" claim about the densest non-PL region. Every single one came from a real reading of the API earlier in the build, but they had been frozen into the markup as bare numbers. Without the review, the dashboard would ship with stale figures drifting silently from the data the API returns. All four were replaced with live API-computed values: hero KPIs compute the benchmark client-side from `listNuts2(limit=500)`; the bar chart reads `topNuts2(limit=15)` and finds its own max. The principle that fell out of this: every number visible to the user should trace back to a call recorded in the network panel. If you can't, it's a lie waiting to happen.

### Cross-extension SQL in one query

A single SQL function feeds Martin's `nuts2_density_tiles`: it joins `lockers` (geography, EPSG:4326) against `nuts2` (PostGIS polygon, EPSG:4326), aggregates by `nuts2_id`, divides by `population_nuts2.value`, runs `ST_AsMVTGeom(ST_Transform(geom, 3857), ST_TileEnvelope(z, x, y), 4096, 64, true)` for the MVT clipping, and returns `bytea`. The trade-off this represents — single-Postgres bundle over best-of-breed services — pays off here. The function is `IMMUTABLE PARALLEL SAFE STRICT` so Postgres parallel-workers it across CPU cores; the daily MV refresh invalidates the inputs but Martin's HTTP cache + per-tile bytea result mean repeat tile requests hit RAM. A 1.1MB MVT response containing 2,477 gminy gets generated in ~150ms in psql, served in ~50ms over HTTP. No cross-service federation, no message bus, no eventual consistency window.

## Trade-offs and explicit cuts

I deliberately did not build a job queue, a CDN, self-hosted basemap tiles, GB regional boundaries, observability tooling, or a 24-hour-fresh velocity timeline. Each of these is the right answer for a different version of this product — Procrastinate the moment ingest needs retries and fan-out; PMTiles on R2 the moment OpenFreeMap throttles or goes down; ONS ITL boundaries when a recruiter asks "what about GB"; Sentry when there's a real user base whose errors I need to catch. None of them are the right answer for a four-day analytics submission with one engineer.

The cuts I'm least comfortable with are around test coverage — the unit tests covering ingest filters and the redaction processor are solid, but spatial joins at country borders deserve property-based testing (Hypothesis) that I didn't write. That's first on the "what I'd build next" list.

## What I'd build with more time

1. **TimescaleDB continuous aggregates for velocity** once 6 months of daily snapshots accumulate — replaces the static press-release timeline.
2. **Backups → Cloudflare R2** wired into pg_cron, not just documented in DEPLOY.md.
3. **PMTiles self-hosted on R2** instead of OpenFreeMap dependency.
4. **ONS ITL boundaries** for GB equivalent to Eurostat NUTS-2 — restores 24,155 GB lockers to the regional density map.
5. **Procrastinate** when scheduling complexity warrants the dependency.
6. **Property-based testing (Hypothesis)** for spatial joins at country borders.
7. **Sentry + Grafana Cloud** for production observability.
8. **Caddy rate-limit module** via xcaddy rebuild (wiring exists in Caddyfile, commented).
9. **CSV / Parquet export endpoints** for the data the dashboard surfaces.
10. **Gminy row click → map flyTo + highlight** for cross-component interaction.

## The numbers

- **150,603** raw records from the InPost API
- **116,086** operating pickup points (active network across 11 markets)
- **31,676** operating PL lockers · **88.7%** open 24/7
- **10.03** lockers per 10k in Wielkopolskie (densest NUTS-2 in EU)
- **2.24** lockers per 10k in Budapest (densest non-PL NUTS-2)
- **4.5×** density ratio, PL vs the rest
- **99.96%** PRG gmina match rate (2,476 of 2,477)
- **33,338** PL lockers spatial-joined to a gmina TERYT
- **2,477** PL gminy · **299** EU NUTS-2 regions
- **14** countries in the catalog · **11** with operating points
- **18** PRs across 4 days · **3** review agents · **9** rule files
- **0** hardcoded values in production (verified by data-integrity audit)
- **0** committed secrets (verified by security audit)

## Closing

The dashboard answers a specific question (how dense is locker access, region by region) with specific numbers from real data. The journey shows how I get from a one-sentence brief to a deployed system through research, narrowing, architectural decisions, phased execution, and review passes that catch what implementation misses.

If you're hiring for engineering judgment under ambiguity, the work speaks for itself.
