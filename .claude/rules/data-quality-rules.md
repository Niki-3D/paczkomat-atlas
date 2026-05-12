# Data Quality Rules — InPost API ingest

Hard filters at ingest. NEVER trust raw API response.

## Exclude on insert
- `address_details.province IN ('test', 'TEST')` (~2% of PL = test fixtures)
- `(location.latitude, location.longitude) == (0, 0)` (null island)
- `status NOT IN ('Operating', 'Created', 'Disabled')`

## Parse with caution
- `opening_hours`: free-text Polish string. Truth is `location_247` boolean for 24/7. Parser is best-effort.
- `operating_hours_extended.customer`: structured but ~2% populated. Minutes-from-midnight encoding.
- `physical_type`: 5 known PL values — `newfm`, `screenless`, `next`, `modular`, `classic`. Unknown → warn, store raw.

## Two networks in one feed
- `type=['parcel_locker']` → InPost Paczkomat machines (~27k in PL)
- `type=['pop']` and variants → PUDO points (~126k EU-wide)
- Headline KPI separates: "27k lockers + 126k PUDOs = 154k total network reach"

## Country codes
- 14 active: PL, FR, GB, DE, ES, IT, AT, SE, PT, HU, DK, FI, BE, NL
- ISO 3166-1 alpha-2. GB not UK.

## Sync strategy
- No ETag/Last-Modified. Full re-crawl per country at `per_page=5000`.
- ~31 requests for full EU. Cron daily 02:00 UTC via GitHub Actions.
- Detect changes via per-record content hash.

## Unknown params silently ignored
- The API does NOT 400 on unknown params. Always assert `count` matches filter intent.
- When adding a filter, log `count_with_filter` vs `count_without_filter`.
