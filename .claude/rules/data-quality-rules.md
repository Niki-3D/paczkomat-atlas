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
- `physical_type`: 8+ known values across all countries:
  - PL: `newfm` (~60%), `screenless` (~21%), `next` (~9%), `modular` (~7%), `classic` (~2%)
  - PL also has: `legacy` (~33 rows), `bankopaczkomaty` (~30 rows, PKO BP partnership)
  - GB also has: `bloqit`
  - Unknown values → warn, store raw, do not exclude

## Two networks in one feed
- `type=['parcel_locker']` → InPost Paczkomat machines (~27k in PL)
- `type=['pop']` and variants → PUDO points (~126k EU-wide)
- Headline KPI separates: "27k lockers + 126k PUDOs = 154k total network reach"

## Country codes

- 14 active: PL, FR, GB, DE, ES, IT, AT, SE, PT, HU, DK, FI, BE, NL
- ISO 3166-1 alpha-2. GB not UK.

### Network composition per country (from full ingest, Phase 3 — n = real)

| Country | Lockers | PUDOs | Operating % | Notes |
|---|---:|---:|---:|---|
| PL | 32,853 | 526 | 96% | Saturated locker-first network |
| GB | 15,065 | 9,153 | 76% | Locker-first; partly via `bloqit` and `legacy` hardware partners |
| FR | 11,959 | 14,618 | 66% | Mondial Relay heavy; growing InPost locker presence |
| IT | 5,848 | 5,272 | 89% | Mixed |
| ES | 4,286 | 10,414 | 75% | Mondial Relay dominant |
| AT | 1,654 | 3,131 | 68% | Mixed |
| HU | 1,283 | 1,436 | 100% | Mixed, fully operational |
| BE | 562 | 1,234 | 77% | Mixed |
| PT | 492 | 2,699 | 73% | PUDO-dominant |
| DE | 0 | 17,460 | 98% | PUDO-only via Mondial Relay (confirmed full ingest) |
| NL | 44 | 1,406 | 69% | PUDO-dominant via Mondial Relay |
| **SE / DK / FI** | **0** | **0** | **0%** | **Pre-launch / decommissioned legacy** — see below |

**SE / DK / FI special case**: 100% of records in these three countries are `Disabled` with `partner_id=99` (Mondial Relay) and a populated `mondial_relay_id`. The entire Nordic footprint is the dormant catalog of the post-acquisition Mondial Relay network; no active InPost-branded points exist in these markets as of 2026. See `docs/recon/05-nordic-status.md` for the investigation. Treat as zero operational reach for KPI purposes; surface the legacy catalog separately if relevant.

The locker/PUDO classification function `is_locker_type()` works correctly across all countries.

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
