# Data Quality Rules — InPost API ingest

Hard filters at ingest. NEVER trust raw API response.

## Exclude on insert

Hard filters applied at ingest. NEVER trust raw API response.

- `address_details.province IN ('test', 'TEST')` — ~2% of PL records are test fixtures
- `name MATCHES /^DGM.*TEST/i` — Italian test fixtures use the `name` field (e.g. `DGMTESTMODULAR`, `DGMTESTNEWFM`), NOT province
- `(location.latitude, location.longitude) == (0, 0)` — null island (FR ~2%, GB ~5.6%, DE/IT 0%)
- `status NOT IN ('Operating', 'Created', 'Disabled', 'Overloaded')` — see status enum below

## Status enum

| Status | Treatment | Notes |
|---|---|---|
| `Operating` | Valid | Default state |
| `Created` | Valid | Not yet live but counted in inventory |
| `Disabled` | Valid | Counted, marked inactive in UI |
| `Overloaded` | Valid | FR-specific, indicates locker temporarily full but operational |
| `NonOperating` | EXCLUDE | GB/IT, semantics unclear — exclude on v1, revisit if needed |
| Other | EXCLUDE | Defensive against future enum additions |

## Parse with caution
- `opening_hours`: free-text Polish string. Truth is `location_247` boolean for 24/7. Parser is best-effort.
- `operating_hours_extended.customer`: structured but ~2% populated. Minutes-from-midnight encoding.
- `physical_type`: 7 known values across all countries:
  - PL: `newfm`, `screenless`, `next`, `modular`, `classic`
  - GB also has: `legacy`, `bloqit`
  - Unknown values → warn, store raw, do not exclude

## Two networks in one feed
- `type=['parcel_locker']` → InPost Paczkomat machines (~27k in PL)
- `type=['pop']` and variants → PUDO points (~126k EU-wide)
- Headline KPI separates: "27k lockers + 126k PUDOs = 154k total network reach"

## Country codes

- 14 active: PL, FR, GB, DE, ES, IT, AT, SE, PT, HU, DK, FI, BE, NL
- ISO 3166-1 alpha-2. GB not UK.

### Network composition per country (from recon, page-1 sample n=500)

| Country | Locker‑heavy | PUDO‑heavy | Notes |
|---|---|---|---|
| PL | 100% | 0% | Saturated machine network |
| GB | ~98% | ~2% | Locker-first market |
| IT | ~77% | ~23% | Mixed |
| FR | ~0.4% | ~99.6% | PUDO-dominant, machines growing |
| DE | ~0% (in sample) | ~100% (in sample) | PUDO-first via Mondial Relay |

Sample biased by API ordering — verify with full ingest. The locker/PUDO classification function `is_locker_type()` works correctly across all countries.

## Address fields — country-specific semantics

`address_details.province` has different semantics per country:

- **PL**: NUTS-2 voivodeship (mazowieckie, śląskie, etc.)
- **GB**: NUTS-1 region (England, Scotland, etc.)
- **IT**: NUTS-3 province (small admin units)
- **FR**: mostly null
- **DE**: mostly null

NEVER aggregate or filter on `province` as a unified concept across countries. Use spatial joins to NUTS-2 boundaries (Eurostat GISCO) for any cross-country geographic aggregation.

## Sync strategy
- No ETag/Last-Modified. Full re-crawl per country at `per_page=5000`.
- ~31 requests for full EU. Cron daily 02:00 UTC via GitHub Actions.
- Detect changes via per-record content hash.

## Unknown params silently ignored
- The API does NOT 400 on unknown params. Always assert `count` matches filter intent.
- When adding a filter, log `count_with_filter` vs `count_without_filter`.
