# Rules Compliance Review

Run by `rules-compliance-reviewer` agent on `chore/pre-deploy-review`, 2026-05-14. Authoritative specs are the files in `.claude/rules/`. Hex-literal violations are owned by `design-review.md` and are not re-litigated here.

## Per-rule scores

| Rule | Score |
|---|---|
| `code-quality.md` | partial |
| `architecture.md` | partial |
| `postgis-conventions.md` | partial → **pass after this commit** |
| `data-quality-rules.md` | pass |
| `dependencies.md` | partial → **pass after this commit** |
| `testing.md` | partial |
| `git-conventions.md` | pass |
| `behavior.md` | pass |
| `design-tokens.md` | (deferred to design-reviewer) |

## What was fixed in this pass

### postgis-conventions.md — pass

Rule: "Hardcoded SRIDs in queries — constants in `db.py`." Three live-code violations fixed:

- `api/src/paczkomat_atlas_api/ingest/sync.py:47` — `SRID=4326` literal in EWKT POINT → now `f"SRID={SRID_WGS84};POINT(...)"`
- `api/src/paczkomat_atlas_api/ingest/sync.py:121` — `ST_Transform(..., 2180)` → bound `:srid_pl` param against `SRID_PL_PUWG`
- `api/src/paczkomat_atlas_api/ingest/eurostat_loader.py:55` — `ST_SetSRID(..., 4326)` → f-string interpolating `SRID_WGS84` with an `# noqa: S608` and rationale (SRID is a module-level int constant, not user input)

Shipped migrations (`5d424a72bd30`, `d6af7bb14d60`) carry SRID literals in GeoAlchemy2 column defs. Migrations are append-only per project rules; flagged as known-deviation for future migrations only.

### dependencies.md — pass

- `shadcn` was listed in `web/package.json` `dependencies` (it's a CLI, not a runtime dep). Moved to `devDependencies`. Lockfile unchanged (the package version reference relocates only).
- `@tanstack/react-table` confirmed in use at `web/components/dashboard/gminy-table.tsx:10-11,169` (the sortable PL gminy table). Adoption was implicit; flagged for the next dependencies.md edit to formally allow-list it.
- No forbidden deps detected (no lodash / moment / axios / pandas).

## What stays as documented findings (deferred)

### architecture.md — partial

- **Raw SQL in `routers/health.py:34,37,40`** — the health endpoint runs three count queries directly. The rule says routers depend on services/repos, not write SQL. Should extract into a `HealthRepo`. Sub-30-min refactor but it touches a heavily-used endpoint mid-pre-deploy; deferring.
- **Repos compose SQL via `text(f"...")`** — accepted deviation, already documented with S608 per-file-ignore + safety comment ("closed predicate set, params bound"). Not a violation to fix; flagged here for transparency.

### code-quality.md — partial

- **File length >300 lines** (target ≤200):
  - `web/components/dashboard/density-map.tsx` — 810+ (MapLibre setup is dense by nature; splitting would help but is a multi-hour refactor)
  - `web/components/dashboard/gminy-table.tsx` — 500
  - `web/components/dashboard/country-share.tsx` — 461
  - `web/components/dashboard/velocity-timeline.tsx` — 295
  - `web/app/page.tsx` — 283
- **Function length >30 lines** (target ≤20):
  - `api/src/paczkomat_atlas_api/ingest/bdl_loader.py:118 load_population_gmina` ≈ 93 lines (the BDL→TERYT match algorithm — non-trivial to split without hurting readability of the algorithm)
  - `api/src/paczkomat_atlas_api/ingest/eurostat_loader.py:72 load_nuts2_population` ≈ 80 lines
- **Function param count >3** in repositories — accepted; the alternative is hand-rolling Pydantic input models for every list endpoint, and FastAPI's `Annotated[Query]` pattern is the documented project convention.
- **Inline `style={{}}` in dashboard components** — widespread, owned by design-review follow-ups (H-5 in that report).
- **Raw `fetch()` in `web/app/page.tsx::probeHealth`** — the probe needs to measure round-trip latency for the nav badge, which the generated SDK doesn't expose. Justified deviation; left as-is with a comment.

### testing.md — partial

Coverage gap (3 files in `api/tests/`):
- `tests/ingest/test_inpost_client.py` — covered
- `tests/ingest/test_inpost_pagination.py` — covered
- `tests/api/test_endpoints.py` — needs running stack; excluded from CI by the same audit pass

Missing per the rule's priority list:
- `bdl_loader.normalize_name` (priority #1 — ingest filter, with diacritic + suffix handling)
- `eurostat_loader` TSV parsing (priority #1 — ingest filter)
- `sync.compute_content_hash` (priority #1 — change-detection)
- Density / spatial-join smoke tests (priority #3, #4)

Coverage target is 75% overall / 90% on ingest filters. Current state is well below; documented as a near-term TODO. Adding the tests is more than the 30-min budget for this task.

## Sign-off

✓ Two rules moved from `partial` → `pass` in this commit (postgis-conventions, dependencies).
✓ Hard violations documented; none block deploy.
✗ Test coverage and inline-style sweep remain the two highest-value follow-ups before v2.
