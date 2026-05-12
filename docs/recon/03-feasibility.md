# Feasibility — storage, tiles, map renderer, indexing

**Probe date:** 2026-05-12. Back-of-envelope sizing based on measured InPost responses.

---

## 1. Database size estimate

### Measured per-locker payload

- Full list-view JSON for one locker ≈ **2 KB** raw (51 fields, lots of nulls; see `recon/samples/probe_per_page_1.json` = 2.4 KB for the whole envelope including 1 item).
- After Postgres `jsonb` binary compression on the long-tail-of-nulls payload, expect ~1.0–1.3 KB stored.

### PL only (34k lockers)

| component                                              | rough size |
|--------------------------------------------------------|-----------:|
| `jsonb` raw payload (34k × ~1.2 KB)                    |     ~40 MB |
| Projected columns (id, name, country, status, lat, lon, city, post_code, physical_type, teryt) | ~6 MB |
| `geometry(Point, 4326)` (32 bytes/row × 34k)           |    ~1.1 MB |
| GIST index on geom                                     |    ~3–5 MB |
| BRIN on `(updated_at, name)` for incremental scans     |    <100 KB |
| **Total PL table footprint**                           | **~50 MB** |

### Global (~153k lockers)

- Linear scaling → **~220 MB** for the lockers table including indexes. Trivially fits in RAM on any Postgres host.

### Time-series of snapshots

- If you store an immutable history (one row per crawl per locker), even hourly crawls for a year = 34k × 24 × 365 = ~300M rows for PL. That's heavy. **Don't do that.**
- Instead, store one current row + a `locker_history` table written only when the content hash changes. Real-world locker churn is single-digit per day → history table grows ~10k rows/year. Tiny.

### Gmina polygons (PRG)

- ~2,477 gmina polygons. PRG simplified to ~50m tolerance is ~30–80 MB for the geometry column. Original at full PRG fidelity can be 200+ MB. **Generalize at ingest** with `ST_SimplifyPreserveTopology(geom, 50)` for choropleth display; keep an un-simplified copy if you need accurate point-in-polygon (or just do the join once and store TERYT on each locker, then drop the high-res polygons).

**Verdict:** total project DB sits comfortably under 1 GB even with generous indexing. Storage is a non-issue.

---

## 2. Vector tiles for the choropleth

Three options for the ~2,477 gmina polygon layer:

### Option A — Pre-baked GeoJSON / TopoJSON (RECOMMENDED for v1)

- Generalize once (`ST_SimplifyPreserveTopology`, target ≤5 MB total).
- Serve a single static `gminy.topojson` file from the CDN.
- Browser loads it once (~1–3 MB gzipped); MapLibre renders it natively.
- **Pros:** zero infra, instant deploy, no tile pipeline.
- **Cons:** all 2,477 polygons present at every zoom (not LOD'd); fine for 2.5k features but would be wrong at 10k+.

### Option B — Tippecanoe → PMTiles, served as static

- `tippecanoe -zg -o gminy.pmtiles gminy.geojson --simplify-only-low-zooms`.
- Single `.pmtiles` file hosted on S3/CDN with HTTP range-request support. MapLibre's `pmtiles://` source loads it lazily.
- **Pros:** scales beyond 2.5k features; gives you a proper LOD pyramid; same hosting story as Option A.
- **Cons:** an extra build step; one more thing to refresh when gmina boundaries change.

### Option C — Martin (live tile server)

- Postgres → Martin reads geom → serves MVT tiles on-the-fly.
- **Pros:** boundaries always reflect DB; can layer choropleth values dynamically per query.
- **Cons:** infra to run (a Go server next to Postgres); cache-warming concerns; overkill for an essentially static boundary layer.

**Recommendation:** start with **A (TopoJSON)**, escalate to **B (PMTiles)** only if you add more layers (powiats, kraje, point clusters as a separate tileset). Skip C until you have a clear dynamic-data reason.

For locker points (153k or 34k), see the next section.

---

## 3. Map renderer for 150k locker points

### Options

|              | License | Cost | Cluster perf @ 150k | WebGL? | Vector tiles | Notes |
|--------------|---------|-----:|--------------------:|--------|--------------|-------|
| **MapLibre GL JS**     | BSD | free        | ✅ smooth via `cluster: true` (Supercluster under the hood); also `circle`/`heatmap` on raw points are fine to ~250k | ✅     | ✅            | Fork of Mapbox GL JS v1; no Mapbox account required |
| **Mapbox GL JS**       | proprietary | 50k free MAUs/mo, then ~$5/1k | same perf | ✅     | ✅            | Same engine, paid plan, fancier built-in styles |
| **Leaflet + MarkerCluster**     | BSD | free | ⚠️ chokes above ~30k unless you also use Leaflet.markercluster + a server-side bbox query | ❌ canvas/DOM | ❌ (raster only out of box) | DOM-driven; great for ≤10k, painful above |
| **deck.gl** (often layered with MapLibre) | MIT | free | ✅ effortless @ 1M+ points | ✅ | ✅ (via base map) | Best for raw scatterplot; heavier API |

### Recommendation: **MapLibre GL JS** as the base + Supercluster (built-in) for clustering.

- 150k points as GeoJSON source with `cluster: true, clusterMaxZoom: 12` is the canonical pattern; renders smoothly on a 2018 laptop.
- If you want individual point WebGL rendering above zoom 12, use a `circle` layer with data-driven opacity.
- For 34k PL-only, MapLibre is laughably overprovisioned — Leaflet would also work, but you'll want clustering anyway, and MapLibre's vector-tile story makes the choropleth easier to compose.

### Avoid

- **Leaflet** for the unclustered case at 150k — DOM markers are dead on arrival.
- **Mapbox GL JS** unless you specifically need their hosted styles. Same engine, no upside for this project.

### Performance ceilings (rough)

- MapLibre + circle layer (no clustering): smooth to ~250k points on a mid-tier laptop, gets sticky around 500k.
- MapLibre + Supercluster: effectively unbounded — clusters do the work.
- deck.gl ScatterplotLayer: 1–5M points smooth, but you're adding a second renderer layer.

---

## 4. Spatial indexing strategy

### GIST on geometry — yes, default

```sql
CREATE INDEX idx_lockers_geom ON lockers USING GIST (geom);
CREATE INDEX idx_gminy_geom   ON gminy   USING GIST (geom);
```

- The one query that matters (`ST_Within(locker.geom, gmina.geom)` to assign TERYT) is GIST-indexed on both sides. With 34k lockers × 2.5k polygons, this runs in seconds even un-tuned.
- For "nearest locker to user" queries, GIST + `<->` operator (KNN) on `ST_Transform(geom, 2180)::geometry` gives meter-accurate distances in <10 ms.

### BRIN on insertion order — only if you have a time dimension

- BRIN shines on a column that **correlates with physical row order** (e.g. `inserted_at` or auto-increment `id` after an `ORDER BY` insert). On a 34k-row table, BRIN saves ~nothing — the whole table fits on a few pages.
- **Justified only for the `locker_history` table** if it grows past ~1M rows: `CREATE INDEX ... USING BRIN (changed_at)` lets you scan a time window without a sequential read of the whole history.

### Other useful indexes

- `CREATE UNIQUE INDEX ON lockers (country, name);` — the natural key.
- `CREATE INDEX ON lockers (teryt) WHERE teryt IS NOT NULL;` — partial index for the choropleth aggregation join.
- `CREATE INDEX ON lockers (status) WHERE status = 'Operating';` — partial index; covers the 95% query path.

---

## 5. Risk register (back-of-envelope, ranked)

1. **API has no incremental-sync hook.** Full re-crawls are cheap (~1 min global), but you can't be lazy. Mitigation: content-hash diff in the ingest job; cron hourly.
2. **~2% of PL records are test data.** Hard-filter at ingest, expose a `is_test` flag rather than silently dropping, so you can audit.
3. **`locker_availability` is a placeholder.** If "is this locker full?" matters to the product, that data lives on a different InPost host that we have not probed.
4. **PRG geometry can shift between releases** (rare, but communes get re-bordered). Re-running the spatial join after a PRG refresh occasionally re-assigns lockers near borders. Plan for it.
5. **ODbL contamination risk.** If you ever fall back to the OSM extract for boundaries (and redistribute the gmina layer), the whole derived layer inherits ODbL. PRG is the safer primary source.
6. **GUS BDL anonymous quota** is tight. Get an API key before any production schedule.
