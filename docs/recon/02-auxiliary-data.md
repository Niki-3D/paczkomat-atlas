# Auxiliary Data Sources — Polish boundaries, population, geocoding

**Probe date:** 2026-05-12. Research only; no downloads performed.

## TL;DR

- **Boundaries → use PRG from GUGiK.** Authoritative, free, includes TERYT codes as attributes (`JPT_KOD_JE`). Native EPSG:2180 (PUWG 1992); reproject lockers to 2180 for distance work, or PRG to 4326 for web display.
- **Population → use GUS BDL REST API**, anonymous reads allowed. Get a free API key for higher quota.
- **Geocoding → not needed.** InPost gives lat/lon. Join to gmina via PostGIS `ST_Within` (or `ST_DWithin` after projecting to 2180).
- **Address normalization → city names alone are not safe joins** (≥30 villages named "Nowa Wieś"). Always spatial-join, never string-join.

---

## 1. Administrative boundaries (gmina / powiat / województwo)

### PRG — Państwowy Rejestr Granic (RECOMMENDED)

- **Owner:** GUGiK (Główny Urząd Geodezji i Kartografii).
- **Landing page (EN):** https://www.geoportal.gov.pl/en/data/national-register-of-boundaries/
- **Open data record:** https://dane.gov.pl/pl/dataset/726 (this is the stable canonical ID — direct shapefile resource is `dane.gov.pl/pl/dataset/726/resource/29515`).
- **Format:** ESRI Shapefile (SHP) and GML. No native GeoJSON, trivial via `ogr2ogr -f GeoJSON -t_srs EPSG:4326`.
- **CRS:** Native **EPSG:2180** (PUWG 1992 / Poland CS92). Reproject as needed.
- **Size:** Boundary-only "jednostki administracyjne" package is ~100–300 MB zipped (full PRG with addresses is GBs — we don't need that).
- **License:** Free for any use since the 2020 amendment to Prawo geodezyjne i kartograficzne. No registration.
- **Freshness:** Updated continuously; monthly/quarterly snapshots.
- **Key attribute:** Each gmina polygon carries `JPT_KOD_JE` = the 7-digit TERYT code. **This makes a name lookup unnecessary** — join lockers to polygons spatially, then read TERYT off the polygon.
- **Ingestion:** `ogr2ogr -f PGDump -lco SCHEMA=geo -t_srs EPSG:2180 gminy.sql gminy.shp | psql ...`. ~10 min one-time.

### OpenStreetMap PL extract (Geofabrik) — fallback

- **URL:** https://download.geofabrik.de/europe/poland-latest.osm.pbf
- **Size:** ~1.5–2 GB PBF (2024 figure; will be larger by now).
- **Freshness:** daily.
- **License:** **ODbL** — share-alike, attribution required. Anything derived from OSM must keep ODbL terms; this is a constraint if you ever redistribute the gmina layer.
- **Extract gmina:** `osmium tags-filter poland.osm.pbf r/admin_level=7 -o gmina.osm.pbf`, then `ogr2ogr` to GeoJSON/PG.
- **Quality:** community-maintained, not authoritative. Topology can disagree with PRG by metres at borders.

### Eurostat GISCO (NUTS / LAU) — backup-only

- **URL:** https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units
- **Formats:** SHP / GeoJSON / TopoJSON / GPKG at multiple generalization scales (1:1M, 1:3M, 1:10M, 1:20M, 1:60M).
- **Granularity:** LAU level = gmina in Poland.
- **Freshness:** annual (LAU 2024 etc.).
- **License:** free, attribution required.
- **Verdict:** geometry coarser than PRG, releases lag by a year. Not recommended unless you specifically need pan-EU comparability.

### Skipped

- **Natural Earth / simplemaps** — stop at admin-1 (województwo). Too coarse.

---

## 2. Population per gmina (GUS — Bank Danych Lokalnych)

### BDL REST API (RECOMMENDED)

- **Base:** `https://bdl.stat.gov.pl/api/v1/`
- **Portal/docs:** https://api.stat.gov.pl/Home/BdlApi
- **PDF reference (method spec):** https://api.stat.gov.pl/Content/files/bdl/Opis_metod_API_BDL_v1.pdf
- **Auth:** anonymous reads work. Free API key raises the quota — request one if you plan more than occasional pulls. Header is `X-ClientId: <key>`.
- **Rate limits:** anonymous is roughly hundreds/day (the docs PDF has exact numbers); registered keys allow tens of thousands. Don't hammer without a key.
- **Formats:** `?format=json` or `xml`.
- **Unit levels (the `unit-level` param):**
  `1`=country, `2`=region (NUTS-1), `3`=województwo, `4`=podregion (NUTS-3), `5`=powiat, `6`=gmina.
- **Population variables:** under subject "Ludność" (P2425 etc.). The classic "ludność ogółem, stan na 31 XII" variable has historically been **id 72305**. Verify the current ID at probe-time:
  - `GET https://bdl.stat.gov.pl/api/v1/variables/search?name=ludność&format=json`
  - `GET https://bdl.stat.gov.pl/api/v1/variables?subject-id=P2425&format=json` (confirmed live during probe)
- **Sample call (all gminas, 2024, anonymous):**
  ```
  GET https://bdl.stat.gov.pl/api/v1/data/by-variable/72305?unit-level=6&format=json&year=2024&page-size=100&page=0
  ```
  Paginate with `page=`. ~2477 gminas → ~25 pages at page-size=100.

### CSV/XLSX direct exports (alternative)

- **"Powierzchnia i ludność w przekroju terytorialnym"** — annual GUS XLSX publication. Search title at stat.gov.pl; the URL changes per edition. One-shot grab for current-year population if you don't want to script BDL.
- Useful for a fast bootstrap; switch to BDL API once you want time series.

### TERYT codes — the join key

- **Structure (7 digits):** `WW PP GG R` — Województwo(2) + Powiat(2) + Gmina(2) + Type(1).
- **Type suffix:** `1`=miejska, `2`=wiejska, `3`=miejsko-wiejska, `4`=miasto w gminie miejsko-wiejskiej, `5`=obszar wiejski w gminie miejsko-wiejskiej.
- **Downloads:** https://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/udostepnianie_danych/baza_teryt/uzytkownicy_indywidualni/pobieranie/pliki_pelne.aspx — free TERC (gmina), SIMC (localities), ULIC (streets). Updated monthly.
- **Already in PRG:** PRG polygons embed the TERYT in `JPT_KOD_JE`. **If you use PRG, you don't need to download TERYT separately** — it's already on each polygon. BDL data joins to that field directly.

---

## 3. Geocoding considerations

### InPost gives lat/lon — no geocoding needed

Confirmed in §4 of `01-inpost-api.md`. Every record carries `location.latitude`, `location.longitude`. **Quality caveat: ~1.5–2% are at (0,0) — filter those out.**

### City/street fields are NOT normalized

From the 500-sample audit:

- **Casing/diacritics required for filtering:** `city=Warszawa` returns 1,760, but `warszawa`/`Warsaw` return 0. So the data **is** stored in the canonical Polish form with diacritics — good.
- **Free-text test data leaks:** `province` is `"test"` for 103 records and `"TEST"` for 561 records (~2% of PL). City fields also contain `"TEST"`. Filter on `province NOT IN ('test','TEST')`.
- **Name collisions:** Poland has ≥30 localities called "Nowa Wieś", plus many "Dąbrowa", "Lipnik", "Borowa", "Aleksandrów" duplicates. A name-only join to gmina will produce 5–10% wrong matches.
- **Polish dzielnice complications:** `city="Warszawa"` covers 18 administrative dzielnice but is a single gmina. `city="Kraków"` similar. For gmina-level work this is fine; for finer dzielnica work, do a second spatial join with a dzielnice layer.

### Recommended join (PostGIS)

```sql
ALTER TABLE inpost_lockers ADD COLUMN geom geometry(Point, 4326);
UPDATE inpost_lockers SET geom = ST_SetSRID(ST_MakePoint(lon, lat), 4326);
CREATE INDEX idx_lockers_geom ON inpost_lockers USING GIST (geom);

-- Project both to EPSG:2180 (metric, more accurate for PL):
ALTER TABLE gminy ALTER COLUMN geom TYPE geometry(MultiPolygon, 2180)
  USING ST_Transform(geom, 2180);

UPDATE inpost_lockers l
SET teryt = g.teryt
FROM gminy g
WHERE ST_Within(ST_Transform(l.geom, 2180), g.geom);
```

Expect ~99.9% match rate after filtering null-island and test rows. Lockers near borders or with bad GPS will be the remaining miss.

---

## Sources

- [PRG dataset (dane.gov.pl)](https://dane.gov.pl/pl/dataset/726)
- [Geoportal PRG (EN)](https://www.geoportal.gov.pl/en/data/national-register-of-boundaries/)
- [Geofabrik Poland extract](https://download.geofabrik.de/europe/poland-latest.osm.pbf)
- [Eurostat GISCO](https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units)
- [BDL API portal](https://api.stat.gov.pl/Home/BdlApi)
- [BDL API method PDF](https://api.stat.gov.pl/Content/files/bdl/Opis_metod_API_BDL_v1.pdf)
- [TERYT download](https://eteryt.stat.gov.pl/eTeryt/rejestr_teryt/udostepnianie_danych/baza_teryt/uzytkownicy_indywidualni/pobieranie/pliki_pelne.aspx)
- [poland-gis-datasets index (sk1me)](https://github.com/sk1me/poland-gis-datasets) — handy aggregated link list
