# Data Model

> PostGIS schema for paczkomat-atlas. See `.claude/rules/postgis-conventions.md` for SRID/operator rules.

## Tables

### `lockers`
| Column | Type | Notes |
|---|---|---|
| `id` | text PK | InPost `name` field (e.g., `KRA01N`) |
| `country` | char(2) | ISO 3166-1 alpha-2 (`PL`, `FR`, …) |
| `type` | text[] | `parcel_locker` / `pop` / variants |
| `status` | text | `Operating` / `Created` / `Disabled` |
| `geom` | `geography(Point, 4326)` | GIST indexed |
| `gmina_id` | text FK | TERYT, nullable for non-PL |
| `nuts2_id` | text FK | Resolved at ingest |
| `physical_type` | text | `newfm`, `screenless`, `next`, `modular`, `classic`, unknown |
| `location_247` | boolean | 24/7 access |
| `raw` | jsonb | Full original API record |
| `content_hash` | text | For change detection |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### `gminy`
| Column | Type | Notes |
|---|---|---|
| `teryt` | text PK | TERYT code (JPT_KOD_JE) |
| `name` | text | |
| `geom` | `geometry(MultiPolygon, 2180)` | GIST indexed |

### `nuts2`
| Column | Type | Notes |
|---|---|---|
| `code` | text PK | NUTS-2 code (e.g., `PL21`) |
| `name` | text | |
| `country` | char(2) | |
| `geom` | `geometry(MultiPolygon, 4326)` | GIST indexed |

### `population_gmina`
- `(teryt, year)` PK · `value bigint`

### `population_nuts2`
- `(code, year)` PK · `value bigint`

## Materialized views

### `mv_density_gmina`
Lockers per 10k inhabitants per gmina. UNIQUE index on `teryt` for concurrent refresh.

### `mv_density_nuts2`
Same for EU.

## Migrations

Alembic, stored in `api/alembic/`. Never edit a shipped migration — create a new one.

## TODO

- [ ] First migration: tables + GIST indexes
- [ ] Seed scripts for PRG + NUTS-2
- [ ] MV definitions + refresh cron
