# InPost Global Points API — Recon

**Endpoint:** `https://api-global-points.easypack24.net/v1/points`
**Probe date:** 2026-05-12
**All raw responses saved under** `recon/samples/`

---

## TL;DR

- API is **multi-country, not PL-only** despite the project framing. 14 country codes return data; PL is ~34k of 153.6k total.
- **No auth required.** No `ETag`, `Last-Modified`, `Cache-Control`, or `X-RateLimit-*` headers. No incremental-sync mechanism.
- **`per_page=5000` works** (probably the practical ceiling; tested up to 10000 in pushes — see below). 31 pages for the full global crawl at 5000/page.
- **Server-side field projection works** via `fields=name,location`. Useful for cheap re-syncs.
- **Geo filter works**, but only via `relative_post_code` + `max_distance`, and **only when `country` is provided**. Lat/lon/bbox parameters are silently ignored.
- **Test data leaks into production**: ~664 records in PL have `province` set to `"test"` or `"TEST"` (~2% of the PL set). Many of these have `latitude=0, longitude=0` (null island).
- **`locker_availability` is NOT live** via this endpoint — every record in a fresh 500-sample showed `status: "NO_DATA"`. Live compartment availability lives elsewhere (probably the mobile/checkout API).

---

## 1. Pagination & scale

| `per_page` | items returned | `total_pages` | response size |
|-----------:|---------------:|--------------:|--------------:|
|         1  |             1  |      153,600  |      2,425 B  |
|        25  |            25  |        6,145  |     54,402 B  |
|       100  |           100  |        1,537  |    220,285 B  |
|       500  |           500  |          308  |    967,582 B  |
|     1,000  |         1,000  |          154  |   1,908,752 B |
|     5,000  |         5,000  |           31  |   9,631,890 B |

- Total `count` was **153,600 → 153,613 over a ~20 min probe window**. Data is live; the catalog drifts by single-digit records continuously.
- `per_page=5000` returns ~9.6 MB per page in ~1 s. **Full global crawl ≈ 31 requests ≈ 31 s** at 1 req/s pacing. Easy.
- I did not push past 5000 (didn't want to risk 429). Probe block left in `recon/probe.py` (`extra` stage) for later.
- Envelope: `{href, count, page, per_page, total_pages, items[], meta}`. `meta` mirrors top-level pagination fields (redundant).

### Headers / incremental-sync prospects

```
Vary: Origin, Access-Control-Request-Method, Access-Control-Request-Headers
Content-Type: application/json
```

- No `ETag`, no `Last-Modified`, no `Cache-Control`, no `Expires`, no `X-RateLimit-*`. (See `recon/samples/per_page_1.headers.txt`.)
- All time-based filter param names I tried (`updated_after`, `updated_since`, `modified_after`) returned the **full unfiltered set** → silently ignored. **No incremental-sync hook exists.**
- Strategy: re-crawl in full. At 31 req/page × 1 s ≈ ~1 min, cheap enough to run hourly if needed. Use a content-hash diff (e.g. xxhash of canonical JSON) per locker to detect changes.

---

## 2. Filters — what works

### Countries (`?country=XX`)

14 country codes returned data; everything else returned `count=0`. Polish project is interested in **PL: 34,009** (~22% of catalog).

| country | count   | country | count   |
|---------|---------|---------|---------|
| PL      | 34,009  | AT      |  4,785  |
| DE      | 17,460  | SE      |  4,454  |
| FR      | 26,718  | PT      |  3,192  |
| GB      | 26,321  | HU      |  2,719  |
| ES      | 14,713  | DK      |  2,375  |
| IT      | 11,161  | FI      |  2,375  |
| BE      |  1,809  | NL      |  1,446  |

Sum ≈ 153,537 → matches the global `count` (drifts ±few dozen). Codes returning 0: `UK` (use `GB`), `CZ`, `SK`, `LT`, `LV`, `EE`, `RO`, `BG`, `HR`, `SI`, `GR`, `IE`, `CH`, `NO`, `US`, `XX`.

### Status (`?status=...`)

PL distribution (`country=PL` + status filter):

| status        | count  | %    |
|---------------|--------|-----:|
| Operating     | 32,179 | 94.6 |
| Created       |  1,653 |  4.9 |
| Disabled      |    166 |  0.5 |
| NonOperating  |      7 |  0.0 |

Sum 34,005 ≈ total PL. **No other statuses observed.** For coverage analysis, filter to `Operating` only — `Created`/`Disabled`/`NonOperating` are pipeline/dead points.

### Type (`?type=...`)

In PL: `parcel_locker=33,479`, `pop=3,098`. Other values (`parcel_point`, `pudo`) returned 0. (Note: `type` is a *list* field on items; one item in the sample had `["parcel_locker", "refrigerated_locker_machine"]` — see §4 anomalies.)

### `physical_type` (`?physical_type=...`)

PL counts: `newfm=18,714`, `screenless=6,219`, `modular=2,683`, `next=2,497`, **`classic=723`** (initially missed because I didn't probe this value — sample audit revealed it).

`physical_type_mapped` is a parallel numeric code: `002=classic, 003=modular, 004=newfm, 005=next, 006=screenless`. (`001` not observed.) Description field `physical_type_description` is **always null** in PL.

### `functions` (`?functions=...`)

Multi-value field. Single-value filter works (e.g. `functions=parcel_collect` → 33,480; `parcel_send` → 34,005). The official enum is also published at **`GET /v1/functions`** (23 entries, with EN-US descriptions — see `recon/samples/sibling_functions.json`):

```
parcel, parcel_send, parcel_collect, parcel_reverse_return_send,
standard_letter_collect, standard_letter_send,
allegro_parcel_collect, allegro_parcel_send, allegro_parcel_reverse_return_send,
allegro_letter_collect, allegro_letter_send, allegro_letter_reverse_return_send,
allegro_courier_collect, allegro_courier_send, allegro_courier_reverse_return_send,
standard_courier_collect, standard_courier_send, standard_courier_reverse_return_send,
air_on_airport, air_outside_airport,
cool_parcel_collect, laundry, avizo
```

Within PL, functions are **near-uniform**: 13 functions appear on 100% of lockers, with `cross_network_parcel_*` on 98.2% and `cool_parcel_collect` on 0.2%. Functions filter is **not a high-information dimension** for PL coverage analysis.

### Geo (`?relative_post_code=NN-NNN&max_distance=N&country=XX`)

- `relative_post_code` **requires `country`** — without it, HTTP 400 `only_one_country_must_be_selected`.
- Returns items sorted by distance ascending, with `distance` field populated **(meters)**. Default cap appears to be 25 results when filter is used without `max_distance`.
- `max_distance` in meters. Example: `?country=PL&relative_post_code=00-001&max_distance=5000` works.
- **Lat/lon, bbox, address are all silently ignored** (return full unfiltered list). Tried params: `latitude`+`longitude`, `lat`+`lon`, `bbox=20,52,22,53`, `address=Warszawa`, `distance=`.
- For a backend coverage analysis: **do the geo work in PostGIS, not via the API.** The lat/lon-per-item is all you need.

### City (`?city=...`)

- **Case-sensitive and diacritic-strict.** `Warszawa` → 1,760. `warszawa` → 0. `Warsaw` → 0. `Kraków` → 809. `Krakow` → 0.
- Useful for hand-checking individual cities, useless for normalization. Use `address_details.city` from full crawl.

### Sparse fields (`?fields=...`)

`fields=name,location` works — response item shrinks from ~2 KB to ~80 B. Server-side projection. Good for cheap delta crawls if we later need to diff coordinates only.

### Other useful filters (all confirmed working with `country=PL`)

- `province=mazowieckie` → 4,776. (Polish lowercase names with diacritics: `śląskie`, `małopolskie`, etc.)
- `post_code=00-001` → 1 (exact match).
- `payment_available=true` → 34,007 (essentially all PL).
- `easy_access_zone=true` → 30,871 (~91% of PL).
- `location_247=true` → 30,203 (~89% of PL).

### Unknown params are silently ignored

`?ZZZ_garbage=foo` returns the full unfiltered set. Same behavior as for ignored geo params. **You cannot detect typos in your queries by response shape** — always sanity-check `count`.

### Error shape

400 errors come back as:
```json
{"status":400,"key":"only_one_country_must_be_selected","error":"Select a country to filter by postcode."}
```

404 for unknown sibling endpoints:
```json
{"status":404,"error":"not_found"}
```

---

## 3. Individual locker endpoint

- **`GET /v1/points/{country}/{name}`** works (e.g. `/v1/points/PL/KRA012`).
- **`GET /v1/points/{name}` alone returns HTTP 400.** Country segment is required.
- Field set is **identical to list-view** — no extra fields. (Diffed key sets: same 51 keys.)
- Therefore the individual endpoint has **no value over a paginated crawl** for ingest. Useful only for spot-checks / live UI.

### Sibling endpoint discovery

Tested under `/v1/`:

| path        | status | notes |
|-------------|-------:|-------|
| `/functions`|    200 | enum of function names + EN descriptions — see above |
| `/countries`|    404 | |
| `/cities`   |    404 | |
| `/types`    |    404 | |
| `/provinces`|    404 | |
| `/stats`    |    404 | |
| `/health`   |    404 | |
| `/metadata` |    404 | |
| `/status`   |    404 | |
| `/providers`|    404 | |
| `/point`    |    404 | |
| `/apm`      |    404 | |

`/v1/functions` is the only "metadata" endpoint that exists. No discovery endpoint for countries, provinces, agencies, etc. — must be derived from the data.

---

## 4. Data shape audit (N=500, country=PL, page 1)

Sampled `recon/samples/sample_500.json` (alphabetic first 500 — heavy A/B-prefix bias) and `recon/samples/sample_500_page35.json` (P-prefix bias). Per-page sorting is **alphabetic by `name`**.

### Field-level presence (out of 500)

**Always present and meaningful** (non-null bool/str/list):
`country, name, status, type, location, location_type, location_category, address, address_details, opening_hours, operating_hours_extended, agency, agencies_extended, functions, physical_type, physical_type_mapped, payment_available, payment_type, easy_access_zone, location_247, is_next, virtual, image_url, locker_availability, mondial_relay_id, express_delivery_send, express_delivery_collect, href`.

**Mostly populated** (small null %): `agency_code` (5% null), `delivery_area_id` (5%), `micro_area_id` (5%), `d2d_courier_area` (5.8%), `d2d_courier_micro_area` (6.2%), `recommended_low_interest_box_machines_list` (21.6%), `location_description_2` (88%).

**Mostly null** (>85%): `air_index_level` (86.4%), `apm_doubled` (90.4%), `operating_hours_extended.customer` (98%), `supported_locker_temperatures` (99.8%), `location_description_1` (100%).

**Always null in PL — drop from schema or store as nullable**: `distance` (only set when geo-filter used), `phone_number`, `location_date`, `physical_type_description`, `print_in_store`, `unavailability_periods`.

### Key distributions (PL, N=500)

- **country**: 100% PL (as expected).
- **status**: Operating 95.2%, Created 4.4%, Disabled 0.4%.
- **physical_type**: newfm 60.6%, screenless 21.0%, next 9.0%, modular 7.4%, classic 2.0%.
- **location_type**: Outdoor 97.0%, Indoor 3.0%.
- **location_category**: Generic 100% (dead field).
- **location_247**: true 98.0%.
- **payment_available**: true 100%.
- **easy_access_zone**: true 100%.
- **air_index_level**: null 86.4%, then VERY_GOOD 9.8%, GOOD 3.6%, SATISFACTORY 0.2%. So when populated it's an ordinal categorical, not a numeric AQI.
- **type** (list): `["parcel_locker"]` 99.8%, `["parcel_locker","refrigerated_locker_machine"]` 0.2%.

### `opening_hours` is a free-text string, not structured

- 97.8% are exactly `"24/7"`.
- Variants seen in just 500 records: `"24//7"` (typo in production), `"PN-SB 06-22"`, `"PN-CZ 10-23 PT-SB 10-23:30"`, etc. (Polish day abbreviations: PN=Mon, WT=Tue, ŚR=Wed, CZ=Thu, PT=Fri, SB=Sat, ND=Sun.)
- **Treat as opaque string for now**; structured form is in `operating_hours_extended.customer` when present.

### `operating_hours_extended` schema (when populated)

98% null. When populated:
```json
{"customer": {"monday":[{"start":360,"end":1320}], "tuesday":[...], ...}}
```
Times are **minutes from midnight** (360 = 06:00, 1320 = 22:00). Each weekday is an array of intervals (supports split shifts).

### `locker_availability` is static placeholder data

Every single record in the 500-sample:
```json
{"status":"NO_DATA","details":{"A":"NO_DATA","B":"NO_DATA","C":"NO_DATA"}}
```
A/B/C are compartment-size buckets (small / medium / large). **This field is dead in the global-points feed** — live availability is exposed only via the consumer/mobile API, not here. Drop it from ingest, or store as a stub.

### Coordinate sanity

- Bounds from N=1000 (two pages combined): lat 0.0–54.63, lon 0.0–23.38.
- **Null island problem**: 7/500 on page 1, 10/500 on page 35 (≈ 1.5–2%) have `lat=0, lon=0`. These are creation-stub records that haven't been geo-located.
- PL legitimate bbox is roughly lat 49.0–54.9, lon 14.0–24.2. After excluding null-island, all observed coords fall inside.
- **Filter rule**: `lat != 0 OR lon != 0` AND `status='Operating'` for any coverage-analysis pipeline.

### TEST data is in production

- `province=test` → **103 records**.
- `province=TEST` → **561 records**.
- Total ≈ **664 test-records (~2% of PL)** mixed into the live feed. Names like `BAT01APP`, `BBI05APP`, `BED03BAPP`, `BEN01APP` (`APP` suffix is a strong tell). Most have null-island coordinates.
- In the sample-500 alone, 7 records had `province` set to `"test"` or `"TEST"`. Easy to filter out.
- **Recommendation**: hard filter on `province NOT IN ('test','TEST') AND latitude != 0 AND status = 'Operating'` for the coverage layer.

### Locker naming convention

- Format observed: `^[A-Z]{2,4}\d{1,3}[A-Z]?(APP)?$` (e.g. `WAW01N`, `KRA012`, `BBI05APP`, `POP-KRA372`).
- 2–4 letter prefix is a **city/locality code**, not a province code. Examples (from sample):
  - `WAW` = Warszawa, `KRA` = Kraków, `BBI` = Bielsko-Biała, `AUG` = Augustów, `PIL` = Piła, `PGD` = Pruszcz Gdański, `LDZ` = Łódź (used as agency too).
- The prefix-to-city map is **inferable but lossy** — many 3-letter prefixes collide with multiple cities (e.g. `ALX` covers ≥3 "Aleksandrów" variants). **Do not use the prefix as a city key**; use `address_details.city` + spatial join.
- The `POP-` prefix marks `type=pop` (partner pickup point) records — name format `POP-XXXNNN`.
- Agency codes (`agency` field) overlap visually with city prefixes but are not the same map (e.g. `BBA` is the Bielsko-Biała agency covering 32% of the A-B alphabetic sample).

---

## 5. Recommended ingest recipe

```
GET /v1/points?country=PL&per_page=5000&page={1..7}
filter:   status='Operating' AND province NOT IN ('test','TEST') AND latitude != 0
store:    everything, but key on (country, name); persist raw JSONB + projected columns (lat,lon,status,physical_type,city,province,post_code)
refresh:  full re-crawl (~7 requests for PL, ~31 globally). Diff via content hash. No ETag available.
geo:      derive gmina via ST_Within(point, gmina_polygon), NOT via API filters.
```

## 6. Open questions / not-tested

- Did not probe `Authorization`/API-key headers (none seem required, but a higher per_page or rate-limit bypass might be unlocked with one).
- Did not push past `per_page=5000`. Saved hook in `recon/probe.py extra` stage.
- Did not probe how often `count` changes — only saw drift of ±20 over ~20 min.
- Did not check if `/v2/` exists.
- Did not look for a WebSocket/SSE channel for live availability.
- Live compartment availability presumably lives on a different host (e.g. checkout/widget). Worth a separate recon pass if the project needs live "is the locker full?" data.
