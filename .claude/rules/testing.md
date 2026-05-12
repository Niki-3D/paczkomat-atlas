# Testing

## Strategy

- Backend: `pytest` + `pytest-asyncio`.
- Frontend: `vitest` + Playwright (later, when there's UI to test).
- Fixtures over setup/teardown.
- Tests mirror source: `api/src/paczkomat_atlas_api/ingest/inpost_client.py` → `api/tests/ingest/test_inpost_client.py`.

## Test types

- **Unit** — mocked HTTP, mocked DB. <10ms each. No network. Default tier.
- **Integration** — real test Postgres+PostGIS via Docker, transaction rollback per test.
- **Smoke** — one end-to-end happy path per major workflow.

## Naming

`test_<what>_<condition>_<expected>`

Examples:
- `test_inpost_client_pagination_returns_all_pages`
- `test_inpost_client_429_retries_with_backoff`
- `test_ingest_filter_excludes_test_province`
- `test_ingest_filter_excludes_null_island`
- `test_density_query_zero_population_returns_null`
- `test_locker_to_gmina_join_match_rate_above_99pct`

## What to test — priority

1. **Ingest filters** — test data exclusion, null island, dedup logic (THE most important)
2. **API client error handling** — 429, timeout, 5xx, malformed JSON
3. **Spatial joins** — locker → gmina, locker → nuts2 match rates
4. **Density calculations** — division by zero, missing population, edge gminas
5. **API endpoints** — response schema, pagination, filters
6. **Materialized view refresh** — concurrent refresh works, data is fresh

## Mocking rules

Mock: InPost API (httpx), GUS BDL API, Eurostat API, file downloads.
Don't mock: database queries, Pydantic validation, Decimal math, PostGIS functions.

Save real API response JSONs in `api/tests/fixtures/` for replay-based tests.

## Coverage

Target: 75% overall. 90% on ingest filters, API clients, density math.

## Commands

```bash
cd api
uv run pytest                           # all
uv run pytest -m unit                   # unit only
uv run pytest api/tests/ingest/         # per-module
uv run pytest --cov --cov-fail-under=75 # with coverage
uv run pytest -k "test_name"            # by name
```

## Forbidden

- `time.sleep()` in tests (use `freezegun` or `pytest-asyncio` fake clock)
- Shared mutable state between tests
- Skipped tests without a tracked issue link
- Order-dependent tests
- `print()` debugging left in tests
- Testing private (`_prefixed`) methods directly
- Hardcoded locker names — use fixtures

## When tests aren't required

Skeleton/scaffolding commits, docs-only changes, infra config tweaks, design token changes. Anything with logic → tests required.
