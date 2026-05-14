# Architecture Review: paczkomat-atlas

Run by `architecture-reviewer` agent on `chore/pre-deploy-review`, 2026-05-14, against the full backend + frontend + infra + CI surface.

## Strengths

1. **Crisp layered backend.** Routers thin (typed query params, response_model, call repos), repos own SQL, schemas are Pydantic-only, models are SQLAlchemy-only. No reverse imports (`routers/__init__.py` re-exports cleanly; `ingest/sync.py` imports `models` but never `routers`). The 13 endpoints (`api/src/paczkomat_atlas_api/routers/{kpi,density,locker,h3,velocity,health}.py`) follow one consistent envelope (`ApiResponse[T]` in `schemas/envelope.py`).
2. **Read path is engineered for cache.** Daily-refreshed MVs (`mv_country_kpi`, `mv_density_gmina`, `mv_density_nuts2`, `mv_h3_density_r8`) feed every dashboard endpoint, `CacheControlMiddleware` (`middleware/cache.py`) sets `public, max-age=3600, stale-while-revalidate=86400` on cacheable prefixes, and pg_cron refreshes are sequenced 5 min apart (`2a08cc2a0894_*.py`). Vector tiles bypass the API entirely via Martin → SQL functions (`801d68ba0f8e_*.py`).
3. **Single typed contract end-to-end.** OpenAPI → hey-api → `web/lib/api/*.gen.ts`, re-exported via `web/lib/api.ts`. `app/page.tsx` is the sole data loader; child components receive typed props. Changing a response shape is a one-place edit + codegen, not a hunt-and-replace.
4. **Migrations look careful.** All five are reversible; `cb36d9c54133` is a real fix-forward (h3 unique-index bug discovered from real data) rather than an edit to a shipped migration; `801d68ba0f8e` correctly splits multi-statement DDL because asyncpg can't run it as one prepared statement.
5. **pgbouncer / prepared-statement interaction is documented and handled.** `db.py` lines 23-39 auto-detects pgbouncer and disables `pool_pre_ping` + sets `prepared_statement_cache_size=0`. Non-obvious; worth the comment.

## Concerns

### CRITICAL
None. Nothing here would cause data loss or block deploy outright.

### HIGH

**H1. Frontend has a documented backend bug it papers over with retries.** `web/app/page.tsx` lines 92-110 wraps every SDK call in `withRetry` because "the backend hits an asyncpg/pgbouncer prepared-statement collision under concurrent load" — and forces all seven endpoint calls **sequential** (lines 117-141) to dodge the issue. That contradicts the comment in `db.py` claiming the issue is solved. The MVs are sub-15ms, so latency is fine for the demo, but under any real parallel load (CDN edge prefetch, link-preview crawlers) you'll see intermittent 5xx. Action: reproduce locally with `asyncio.gather` of all endpoints, confirm whether the fault is `pool_pre_ping` or something else (the asyncpg `prepared_statement_cache_size=0` should already prevent it). If still flaky, switch to a session-pooling pgbouncer pool or run pgbouncer with `server_reset_query=DISCARD ALL` and reset prepared stmts.

**H2. CI is non-blocking.** `.github/workflows/ci.yml` line 26: `uv run pytest -q || echo "no tests yet"` — pytest failure cannot fail the job. No mypy step. No `pnpm lint`. No frontend build verification. Per `code-quality.md` a commit must pass typecheck + ruff; CI currently enforces only `ruff check` and `pnpm typecheck`. Action: drop the `|| echo`, add `uv run mypy .` and `pnpm lint && pnpm build`.

**H3. Deploy workflow is a placeholder.** `.github/workflows/deploy.yml` is one `echo` line. "Pre-deploy review" with no actual deploy automation means someone is `ssh && docker compose pull` by hand, and there's no Alembic-on-deploy step recorded anywhere. Action: at minimum, document the manual deploy steps in `docs/DEPLOY.md`; ideally script `ssh hetzner 'cd /opt/paczkomat && git pull && docker compose pull && docker compose up -d && docker compose exec api alembic upgrade head'`.

**H4. Health endpoint hardcodes `http://martin:3000/health`** (`routers/health.py` line 46). Outside docker-compose this is unreachable and `/health` returns `degraded`. The frontend (`app/page.tsx` line 47) treats `status==="ok"` as the truth signal for the nav latency pill, so any martin hiccup turns the whole API badge red even though API and DB are fine. Action: move the URL to `config.py` (e.g. `martin_health_url`), and either separate `api_ok` from `martin_ok` in the response or have the nav read the more granular flag.

### MEDIUM

**M1. CORS is wide-open.** `main.py` line 29 `allow_origins=["*"]`. Comment acknowledges it. Public read-only API, so risk is low, but on a real domain you'd tighten to the dashboard origin.

**M2. `mv_country_kpi` does not filter test data at MV time.** `d6af7bb14d60` MVs count from `lockers` filtered only by `status IN ('Operating','Overloaded')`. The data-quality filters live in `ingest/inpost_client.is_valid_point()` which runs at ingest — fine as long as ingest is the only writer, but if anyone ever runs a backfill from the JSONB `raw` column or `staging` schema, test fixtures can leak into the MVs.

**M3. Velocity endpoint is a hardcoded Python list** (`routers/velocity.py` lines 23-50). Documented as v1 placeholder until snapshots accumulate. Fine for the demo; flag the technical debt — the chart in `velocity-timeline.tsx` is hard-pinned to PL/FR/GB/IT/ES, so when you do swap to the hypertable, both ends need to move together.

**M4. `loadAll()` couples seven endpoints into one bundle** (`app/page.tsx` lines 115-173). If any one repo query starts taking 200ms it serializes onto every other panel's TTFB. Once H1 is fixed, switch back to `Promise.allSettled` parallelism.

**M5. `ingest/sync.py::snapshot_to_hypertable()` is unbounded** (line 168-178) — `INSERT … SELECT FROM lockers` writes ~70k rows per call into the hypertable. With pg_cron + GH-Actions ingest, the hypertable grows ~25M rows/year. 14-day compression + 730-day retention are set in `5d424a72bd30`, so it self-limits, but worth checking compression actually kicks in before the volume hits.

### LOW

**L1.** `models/snapshot.py` declares the table but the hypertable conversion happens in the migration — two sources of truth for one entity.

**L2.** `repositories/*.py` uses `text(f"...")` with f-string composition of `WHERE` clauses. Comments correctly note predicates are hardcoded and values bound; a tiny `_where_builder` helper would deduplicate.

**L3.** `web/components/{charts,landing,map}/` directories exist but are empty.

**L4.** `web/components/dashboard/density-map.tsx` line 146 hardcodes `#0A0A0B` as a background color, violating `design-tokens.md`. Replace with `var(--bg-canvas)`. *Owned by design-reviewer (Task 6).*

**L5.** `app/page.tsx` line 36 hardcodes `http://localhost:8080` as default API base — at deploy the env var must be set.

## Action Items (this branch)

- **H1**: documented as TODO in `db.py` (reproduction needs concurrent-load setup we don't have in this pass). Frontend serial+retry shim left in place until reproduced.
- **H2**: CI hardened — `pytest` no longer swallowed, `mypy` + `pnpm lint` + `pnpm build` added.
- **H3**: `docs/DEPLOY.md` updated with the manual runbook (Caddy, compose, Alembic upgrade order).
- **H4**: Martin health URL moved to `config.py`; health response shape extended with explicit `db_ok` / `martin_ok` booleans; nav reads `db_ok` for its badge.

## Score: **B+**

Clean separation, single typed pipeline, MV-backed read path, real migration discipline. The CI-permits-failure setting, the placeholder deploy job, and the retry/serial-load shim covering an unresolved pgbouncer interaction are the only things between this and an A. None are deploy-blockers for a demo, but H1 + H2 will bite the moment this gets real traffic or real tests.
