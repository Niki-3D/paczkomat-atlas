# Cross-Country API Recon — FR, GB, DE, IT

**Date:** 2026-05-12
**Method:** 500-record sample from page 1 of `GET /v1/points?country=<XX>&per_page=500` per country (`docs/recon/samples/cross_country/sample_<XX>_500.json`). Spot examples per observed `physical_type` extracted from the same samples (`example_<XX>_<type>.json`).
**Caveat:** 500 records is page-1 only, so the locker/PUDO **mix** in this sample is order-dependent. Field **semantics** (which fields exist, what enum values appear) are robust at this sample size. Totals are taken from the API's `count` field, not the page.

---

## TL;DR

- **Classification logic holds.** `"parcel_locker" in type` correctly identifies machines across all four countries. The PUDO marker `("pok", "pop")` is universal.
- **Enum drift is real.** `physical_type` gains `legacy` and `bloqit` (GB). `status` gains `Overloaded` (FR) and `NonOperating` (GB, IT). Both must be added to allowed-value lists.
- **Test data is country-specific.** Filtering `province IN ('test','TEST')` is PL-only. IT puts test markers in the `name` field (e.g. `DGMTESTMODULAR`). FR/GB/DE samples had zero detectable test records.
- **`province` is sparsely populated outside PL.** FR has it for 0.4% of records, DE for 0%. The column must be nullable; do not rely on it for any non-PL logic.

---

## 1. Totals — match previous recon?

| Country | API `count` | Prior estimate | Δ |
|---|---:|---:|---|
| FR | 26,698 | 27k | ≈ |
| GB | 26,322 | 26k | ≈ |
| DE | 17,460 | 17k | ≈ |
| IT | 11,161 | 11k | ≈ |

All four within ~2% of the previously reported figures. No surprises.

## 2. Does `parcel_locker` in `type` exist outside PL? Yes — with very different prevalence

| Country | `('parcel_locker',)` | `('pok','pop')` | Other |
|---|---:|---:|---|
| FR | 2 (0.4%) | 498 (99.6%) | — |
| GB | 491 (98.2%) | 9 (1.8%) | — |
| DE | 0 (0.0%) | 500 (100%) | — |
| IT | 387 (77.4%) | 113 (22.6%) | — |

`type` is the same multi-value list across all countries; the **only** observed tuples in the 4-country sample are `('parcel_locker',)` (= machine) and `('pok','pop')` (= PUDO). No third pattern.

`classify_locker_or_pudo()` semantics: `"parcel_locker" in type` → locker; everything else → PUDO. **Works unchanged cross-country.**

The DE 0% lockers in the page-1 sample is striking — DE may genuinely be PUDO-dominant, or page-1 happens to be biased. Either way it does not change the classifier logic.

## 3. Locker vs PUDO split (page-1 sample, n=500/country)

| Country | Lockers | PUDOs | Locker share |
|---|---:|---:|---:|
| FR | 2 | 498 | 0.4% |
| GB | 491 | 9 | 98.2% |
| DE | 0 | 500 | 0.0% |
| IT | 387 | 113 | 77.4% |

GB and IT lead with lockers; FR and DE are PUDO-heavy networks. Numbers are from page 1 and are not a population-level ratio — full per-country splits need a paginated full pull (Phase 1 work).

## 4. Does `is_valid_point` filter apply unchanged?

### 4a. `province=='test'` test-data marker — PL-only

| Country | `province IN ('test','TEST')` | `'TEST' in name` |
|---|---:|---:|
| FR | 0 | 0 |
| GB | 0 | 0 |
| DE | 0 | 0 |
| IT | 0 | **2** (`DGMTESTMODULAR`, `DGMTESTNEWFM`) |

**Surprise:** IT marks test fixtures in the `name` field, not `province`. The records have plausible Italian addresses (`Altopascio, FI`), real-looking provinces, and `status='Created'`. Without name-based filtering they would slip through.

Recommendation: filter must be country-aware **or** uniformly check both `province` and a name-regex (`/^DGM.*TEST/i` covers the IT pattern; consider `/TEST/i` as a broad safety net but verify it doesn't false-positive against legitimate stores).

### 4b. Null island

| Country | `(lat,lon) == (0,0)` |
|---|---:|
| FR | 10 / 500 (2.0%) |
| GB | 28 / 500 (5.6%) |
| DE | 0 |
| IT | 0 |

Still occurs, still needs filtering. GB has the highest rate by a wide margin.

### 4c. `status` enum — expanded

| Country | Statuses observed |
|---|---|
| FR | `Operating`, `Disabled`, **`Overloaded`** |
| GB | `Operating`, `Created`, `Disabled`, **`NonOperating`** |
| DE | `Operating`, `Disabled` |
| IT | `Operating`, `Created`, `Disabled`, **`NonOperating`** |

`data-quality-rules.md` currently says `status NOT IN ('Operating', 'Created', 'Disabled')`. Two new values appear:

- **`Overloaded`** (FR, 1 record / 0.2%) — almost certainly a locker that has too much volume; treat as a transient operational state, probably want to **include**.
- **`NonOperating`** (GB 8/500 = 1.6%, IT 1/500 = 0.2%) — looks like a soft-deleted / decommissioned state distinct from `Disabled`. Probably want to **exclude**, but we should confirm with a sample.

Decision needed from human, not from this recon.

## 5. `physical_type` per country

PL set (from `data-quality-rules.md`): `newfm`, `screenless`, `next`, `modular`, `classic`.

| Country | Observed `physical_type` values |
|---|---|
| FR | `newfm` (lockers only); `null` for PUDOs |
| GB | `newfm`, **`legacy`**, **`bloqit`**; `null` for PUDOs |
| DE | `null` only (no lockers in sample) |
| IT | `newfm`, `modular`; `null` for PUDOs |

**Two new values** to add to the documented enum: `legacy` and `bloqit` (both GB-only in this sample).

- `bloqit` is the third-party Bloq.it locker hardware vendor — GB partnered with them for early UK rollout.
- `legacy` is older-generation hardware. The `physical_type_mapped` field on legacy records carries `'001'` — possibly a numeric code for a deprecated taxonomy.

Neither value appeared in the PL recon. Updating the rules file should be **its own commit** after human approval (per `behavior.md` — rule files encode decisions).

## 6. `address_details` — same 6 fields everywhere, populated unevenly

All four countries return the same 6 keys: `city`, `province`, `post_code`, `street`, `building_number`, `flat_number`.

`province` populated rate:

| Country | province populated |
|---|---:|
| FR | 2 / 500 (0.4%) |
| GB | 500 / 500 (100%) — values are UK regions: `London`, `Scotland`, `Wales`, … |
| DE | 0 / 500 (0%) |
| IT | 500 / 500 (100%) — values are Italian 2-letter province codes: `AG`, `AL`, `AN`, … |

PL (from prior recon) populated `province` with voivodeship names.

The semantics are **different across countries**:
- PL: voivodeship (level NUTS-2)
- GB: macro-region (level NUTS-1)
- IT: provincia (level NUTS-3)
- FR/DE: mostly empty; FR uses macro-regions ("NORD IDF", "Ouest") when present

→ `province` in our `lockers` table must be `text NULL`. **Never** join on it across countries; use the geometry → NUTS-2 spatial join from the boundary tables instead.

## 7. `opening_hours` and `location_247`

| Country | `location_247=True` | `opening_hours` samples |
|---|---:|---|
| FR | 14 / 500 (2.8%) | mostly `None`, occasional `'24/7'` |
| GB | 475 / 500 (95.0%) | almost always `'24/7'` |
| DE | 6 / 500 (1.2%) | all `None` |
| IT | 279 / 500 (55.8%) | mostly `None` |

`opening_hours` is a free-text field with no language consistency (and is mostly null outside PL/GB). `location_247` is the only reliable signal for 24/7 access — same as PL. Free-text parsing across languages is not worth doing.

## 8. `functions` field — top values

GB and IT (locker-heavy) cluster on `parcel`, `parcel_collect`, `parcel_send`. FR and DE (PUDO-heavy) add `standard_courier_*` and `standard_letter_*` variants — these are PUDO-only functions.

`cross_network_parcel_collect` / `cross_network_parcel_send` appear at 60–99% rate in FR, DE, IT but **0% in GB**. Likely indicates GB lockers aren't yet wired into the cross-network routing — a business detail, not a schema one.

The `functions` field is high-cardinality (15+ distinct values). Store as `text[]` on the `lockers` table; do not enum it.

## 9. Unexpected fields

Same 51 top-level keys appear in every country sample. No truly new fields, but two are notable:

- **`mondial_relay_id`** — populated for FR PUDOs (`'00000'` style ID), confirming that FR PUDO points are the Mondial Relay partner network. Likely null in PL/GB/DE/IT.
- **`locker_availability.status`** — `NO_DATA` for FR/DE/IT (100%); GB exposes real availability tiers (`NORMAL` / `LOW` / `VERY_LOW`, with `NO_DATA` for 2%). GB-only live data could power a "locker fullness" panel, but it's GB-only — not portable as a core KPI.
- **`physical_type_mapped`** — typically null, but `'001'` on GB `legacy` records. Might be a vendor SKU map; not worth modelling yet.

---

## Implications for schema (Phase 1)

| Question | Answer | Action |
|---|---|---|
| Does `classify_locker_or_pudo()` need updating? | **No** — `"parcel_locker" in type` works unchanged for all four countries. | None. Keep current logic. |
| Does `is_valid_point()` need country-specific filters? | **Yes** — IT puts test markers in `name`. PL puts them in `province`. | Add a name regex check (`/^DGM.*TEST$/i` covers observed IT cases; suggest also broadening to `province ILIKE 'test'` plus per-country test-prefix list). |
| Should `province` on `lockers` be nullable? | **Yes** — null for 99.6% of FR and 100% of DE in this sample. | Migration: `province TEXT NULL`. Never use it for cross-country aggregation; rely on spatial join to NUTS-2/gminy instead. |
| Any new `physical_type` values to document? | **Yes** — `legacy`, `bloqit` (both GB). | Propose update to `data-quality-rules.md` (diff below). |
| Any new `status` values to document? | **Yes** — `Overloaded` (FR), `NonOperating` (GB, IT). | Propose update to `data-quality-rules.md` (diff below). Need a decision on whether `NonOperating` filters out. |

## Proposed diff to `.claude/rules/data-quality-rules.md` (NOT applied — separate commit after human approval)

```diff
 ## Exclude on insert
-- `address_details.province IN ('test', 'TEST')` (~2% of PL = test fixtures)
+- `address_details.province IN ('test', 'TEST')` (~2% of PL = test fixtures)
+- `name ~* '^DGM.*TEST'` (IT test fixtures — `DGMTESTMODULAR`, `DGMTESTNEWFM`)
 - `(location.latitude, location.longitude) == (0, 0)` (null island)
-- `status NOT IN ('Operating', 'Created', 'Disabled')`
+- `status NOT IN ('Operating', 'Created', 'Disabled', 'Overloaded')` — `Overloaded` is a transient operational state (FR), keep
+- Decision needed: `NonOperating` (GB, IT) — looks distinct from `Disabled`; default-exclude until confirmed
 
 ## Parse with caution
 - `opening_hours`: free-text Polish string. Truth is `location_247` boolean for 24/7. Parser is best-effort.
+- `opening_hours` is mostly null in FR/DE/IT and `'24/7'`-literal in GB. Cross-country: always trust `location_247` boolean, ignore the string.
 - `operating_hours_extended.customer`: structured but ~2% populated. Minutes-from-midnight encoding.
-- `physical_type`: 5 known PL values — `newfm`, `screenless`, `next`, `modular`, `classic`. Unknown → warn, store raw.
+- `physical_type`: 7 known values across observed countries — PL: `newfm`, `screenless`, `next`, `modular`, `classic`; GB-only: `legacy`, `bloqit`. Unknown → warn, store raw.
```

## Surprises that affect the Phase 1 plan

1. **IT test markers in `name`** — add a name regex check to `is_valid_point()` before the first IT ingest.
2. **`province` semantics differ across countries (NUTS-1 vs NUTS-2 vs NUTS-3)** — do not project anything on `province` cross-country. Spatial join to NUTS-2 polygons is the only reliable way to bin.
3. **GB-only live `locker_availability`** — interesting product opportunity, but don't put it on the critical path; it doesn't generalize.
4. **DE has zero lockers in the page-1 sample** — likely PUDO-only or PUDO-dominant. Worth confirming with a full pull before promising a DE "lockers per 10k" choropleth. If DE is genuinely 100% PUDO, the headline KPI needs different framing for it.
5. **`NonOperating` decision pending** — 9 records across GB+IT in this sample. Need to either inspect a few and decide, or default-exclude.

No findings that block Phase 1 schema work — the lockers table shape is unchanged. The classifier and validator need minor tweaks; both are isolated functions.
