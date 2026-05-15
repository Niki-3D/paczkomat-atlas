# Data Integrity Audit

Generated 2026-05-14 on `chore/pre-deploy-review`. Verified every visible number on the dashboard traces to a real API call or a credibly-sourced static dataset. Zero "looks roughly right" values shipped.

## Component-by-component trace

| Component | Data source | Verified | Notes |
|---|---|:---:|---|
| `app/page.tsx::probeHealth` | `GET /api/v1/health` | ✓ | Used for API status pill + locker count in footer |
| `app/page.tsx::computeBenchmark` | `listNuts2({ limit: 500 })` sorted in memory | ✓ | Returns `{ topPl, topNonPl, ratio }` live — NOT hardcoded |
| `hero-kpis.tsx` KPI #1 (network total) | `summary.n_network_total` from `getNetworkSummary` | ✓ | Plus lockers/PUDO split, active countries |
| `hero-kpis.tsx` KPI #2 (PL lockers) | `pl.n_lockers` + `pl.pct_247` + `pl.n_247` from `listCountryKpis` | ✓ | All live |
| `hero-kpis.tsx` KPI #3 (density ratio) | `benchmark.ratio` (live) | ✓ | Was already wired live |
| `density-bars.tsx` 15 bars | `rows` from `topNuts2({ limit: 15 })` | ✓ | |
| `density-bars.tsx` benchmark line + caption | `benchmark` prop (live) | ✓ **fixed** | See "Hallucinations found" below |
| `density-map.tsx` choropleth + tooltip | Martin tiles + feature properties | ✓ | Tiles backed by mv_density_nuts2 / mv_density_gmina |
| `density-map.tsx` heatmap | Martin `lockers_tiles` | ✓ | Filtered to Operating+Overloaded server-side |
| `country-share.tsx` per-country bars | `rows` prop = `listCountryKpis().data` | ✓ | Locker share + PUDO share computed from props |
| `country-share.tsx` "Pre-launch" badges (SE/DK/FI) | derived from `n_total === 0` | ✓ | Programmatic, not hardcoded list |
| `velocity-timeline.tsx` 5 country lines | `points` prop = `getVelocity().data` | ✓ | Static dataset by design; see §"Velocity disclosure" |
| `velocity-timeline.tsx` growth multiples | computed live from `series[0]` vs `series[length-1]` | ✓ | |
| `gminy-table.tsx` rows + sortable columns | `rows` prop = `listGminy({ limit: 2500 })` | ✓ | All sorting/filtering client-side on live data |
| `footer.tsx` total records | `totalRecords` prop = `/health.locker_count` | ✓ | Live |
| `footer.tsx` data source labels (PRG 2022-06-27, Eurostat 2024, GUS BDL 2024) | factual citations | ✓ | Match project briefing §15 + ingest loaders |
| `nav.tsx` API status pill + latency | `probeHealth()` result | ✓ | |

## Hallucinations found — and fixed

### `density-bars.tsx` (4 hardcoded values)

Before this audit:

1. `const BUDAPEST_BENCHMARK = 2.24;` — module constant
2. `"All 15 are Polish voivodeships. 16th place: PL Mazowieckie at 7.43."` — hardcoded subtitle
3. `"Budapest 2.24 — top non-PL region"` — hardcoded annotation chip
4. `"Wielkopolskie at 10.06 is 4.5× denser"` — hardcoded caption

**Why it was wrong:** these values shift whenever the daily ingest refreshes the MVs. The Top-15 ordering is stable but the *exact* densities float as new lockers are added. The page-level `computeBenchmark()` already returns the same numbers live; the component just wasn't receiving them.

**Fix applied:** added `benchmark: DensityBenchmark` prop to `DensityBars`, wired through `page.tsx`. The annotation chip now reads `{nonPl.name} {fmt2(nonPl.density)} — top non-PL region`; the caption reads `{topPl.name} at {fmt2(topPl.density)} is {fmt1(ratio)}× denser`. All three numbers come from the prop. The "16th place at 7.43" claim was removed entirely — that 16th datapoint wasn't fetched and would also drift.

The line position `annotLeftPct` now derives from `nonPl.density / max` instead of `BUDAPEST_BENCHMARK / max`.

### Nothing else found

Searched the full `web/components/` tree for:
- Magic numbers matching the briefing's story values (`2.24`, `10.06`, `4.5`, `150,?599`, `116,?965`, `31,?687`, `88\.5`, `69,?771`, `47,?194`)
- Hardcoded region names (`Wielkopolskie`, `Budapest`, `Mazowieckie`, etc.)
- Hardcoded `country: "X"` or status literals

Only matches were:
- `density-bars.tsx` — fixed (above)
- One factual reference in a code comment (acceptable)

## Velocity disclosure (intentionally static)

`api/src/paczkomat_atlas_api/routers/velocity.py` has 21 hardcoded `VelocityPoint` rows for PL / FR / GB / IT / ES, 2022-12-31 → 2025-06-30. The router's docstring explicitly cites sources:

> Sources: InPost SA annual report 2024 (filed 2025-03), Q3 2024 trading update, Q1 2025 trading update, FR market entry announcement Sep 2024.

Each row is tagged `source: "press_release"`. The frontend disclosure in `velocity-timeline.tsx` reads "Locker counts from InPost public press releases · {first date} → {last date}". This is the only static dataset surfaced to the UI; it's correctly labeled.

## Future state

When the TimescaleDB hypertable has ≥6 months of daily snapshots, velocity should switch to a continuous aggregate (`velocity_daily_country`) backed by `ingest_snapshots`. That replaces the static router with a live one. Until then the press-release dataset is the honest answer.

Footer URLs `http://localhost:8080/docs` and `/catalog` will need to be swapped for the production domain at deploy time. Not a hallucination, but a TODO for the deploy step.

## Sign-off

✓ Every UI number traces to a live API call OR a labeled static dataset with cited source.
✓ Zero ad-hoc "looks plausible" magic numbers remain in the visible UI.
✓ `pnpm typecheck` passes after fix.
