# Deploy

Production runs on a shared Hetzner CX22 (4 vCPU, 8 GB, Ubuntu 24.04) at
`62.238.7.125`. SSH user `doppler`. Another project (Doppler) shares the host
with 8 containers on its own docker network — never touch `/home/doppler/doppler/`.

Architecture:

- Caddy bound to `0.0.0.0:80` and `0.0.0.0:443` is the ONLY public surface.
- All other services (db / pgbouncer / martin / api / web) live on the
  isolated `paczkomat_net` docker network, reachable only from inside.
- Postgres data bind-mounted at `/home/doppler/paczkomat-atlas/data/db`
  so `pg_dump` and rsync work from the host.

## Live URL

Until Niki points DNS, the dashboard is reachable directly at:

- http://62.238.7.125/ — dashboard (Next.js)
- http://62.238.7.125/api/v1/health — API health JSON
- http://62.238.7.125/docs — Swagger UI
- http://62.238.7.125/catalog — Martin tile catalog
- http://62.238.7.125/tiles/{layer}/{z}/{x}/{y} — MVT tiles

DNS record to set when ready:

```
A    <hostname>    →    62.238.7.125    (TTL 300)
```

After DNS propagates, update `.env.production` on the server:

```bash
ssh doppler@62.238.7.125
cd /home/doppler/paczkomat-atlas
# Edit .env.production:
#   PUBLIC_HOSTNAME=<hostname>             (drop the http:// prefix)
#   NEXT_PUBLIC_API_BASE_URL=https://<hostname>
#   CORS_ORIGINS=https://<hostname>
docker compose -p paczkomat \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.prod.yml \
  --env-file .env.production up -d --build web caddy
```

Caddy will auto-provision the Let's Encrypt cert on first request. TLS
should be live within ~60 seconds.

## First deploy (already done — for reference)

`scripts/deploy.sh` automates the flow. It assumes the server already has
Docker, `git`, `openssl` (Ubuntu 24.04 default).

```bash
./scripts/deploy.sh                  # full deploy of current branch
./scripts/deploy.sh --skip-build     # no image rebuild
./scripts/deploy.sh --skip-migrate   # no alembic
./scripts/deploy.sh --branch main    # deploy a different branch

# One-off: push gitignored static data (PRG/Eurostat/GUS) to the server.
./scripts/deploy_data.sh
```

The first run generated `.env.production` on the server with fresh
`openssl rand -base64 32` passwords. Subsequent runs don't touch it.

## What lives where on the server

```
/home/doppler/paczkomat-atlas/
├── .env.production              # ← secrets, 0600, NEVER committed
├── data/
│   ├── db/                      # ← Postgres data dir (bind mount)
│   └── raw/                     # ← Eurostat/GUS/PRG, mounted ro into api
├── infra/compose/...
├── scripts/...
└── ...                          # rest is the repo
```

`docker volume ls --filter name=paczkomat`:
- `paczkomat_caddy_data`  — Caddy's Let's Encrypt certs
- `paczkomat_caddy_config`

## Ingest data on first deploy

The ingest CLI lives in the api container. Run from the host:

```bash
ssh doppler@62.238.7.125
cd /home/doppler/paczkomat-atlas
set -a; . ./.env.production; set +a

# Helper alias for the rest of this section
DC="docker compose -p paczkomat \
    -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml \
    --env-file .env.production"

# Ingest uses the ADMIN role via the direct DB connection (asyncpg+pgbouncer
# has an open prepared-statement issue under transaction-mode pooling).
INGEST_DB="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

# 1. InPost lockers + PUDOs (~150k records, all 14 active countries)
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --all

# 2. Eurostat NUTS-2 boundaries
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --load-nuts2

# 3. NUTS-2 spatial assignment
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --assign-only

# 4. Eurostat NUTS-2 population (skips gmina population — needs PRG)
$DC exec -T -e DATABASE_URL="$INGEST_DB" api uv run python -c "
import asyncio
from paczkomat_atlas_api.ingest.eurostat_loader import load_nuts2_population
from paczkomat_atlas_api.logging import configure_logging
configure_logging()
print(asyncio.run(load_nuts2_population()))
"

# 5. Refresh all MVs
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --refresh-only
```

## PRG (gmina boundaries) ingest

`prg_loader.py` shells out to `docker run gdal` — that needs the docker
socket inside the api container, which we won't mount. Instead, a separate
one-shot compose service `prg-loader` runs ogr2ogr once and exits.

```bash
# 0. One-time: ship the PRG shapefile from your laptop. ~85 MB shp + 4 MB dbf.
tar -czf - data/raw/prg/A03_Granice_gmin.{shp,shx,dbf,prj} | \
  ssh doppler@62.238.7.125 'cd /home/doppler/paczkomat-atlas && tar -xzf -'

# 1. Load shapefile into staging.gminy_prg (SRID 2180, PROMOTE_TO_MULTI).
$DC --profile loader run --rm prg-loader

# 2. Merge staging → gminy + compute areas. Lives in prg_loader.py.
$DC exec -T -e DATABASE_URL="$INGEST_DB" api uv run python -c "
import asyncio
from paczkomat_atlas_api.ingest.prg_loader import merge_staging_to_gminy, compute_areas
from paczkomat_atlas_api.logging import configure_logging
configure_logging()
async def main():
    print('merged:', await merge_staging_to_gminy())
    print('areas:', await compute_areas())
asyncio.run(main())
"

# 3. Spatial-join PL lockers to gminy.
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --assign-only

# 4. GUS BDL gmina population (needs PRG loaded first — joins on teryt/name).
$DC exec -T -e DATABASE_URL="$INGEST_DB" api uv run python -c "
import asyncio
from paczkomat_atlas_api.ingest.bdl_loader import load_population_gmina
from paczkomat_atlas_api.logging import configure_logging
configure_logging()
print(asyncio.run(load_population_gmina()))
"

# 5. Refresh all MVs.
$DC exec -T -e DATABASE_URL="$INGEST_DB" api \
    uv run python -m paczkomat_atlas_api.ingest.cli --refresh-only

# 6. Bust Martin's tile cache so the new gminy_density tiles render.
ssh doppler@62.238.7.125 'docker restart paczkomat-martin'
```

Verification: ~2477 rows in `gminy`, ~2422 in `population_gmina`,
~2417 nonzero in `mv_density_gmina`. API smoke test:

```bash
curl -s http://62.238.7.125/api/v1/density/gminy/top?limit=3 | jq .data
# Expect: Kuślin / Rudziniec / Manowo with lockers_per_10k > 15.
```

## Rollback

```bash
ssh doppler@62.238.7.125 'cd /home/doppler/paczkomat-atlas && \
  git fetch origin && \
  git reset --hard <previous-sha> && \
  docker compose -p paczkomat -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml --env-file .env.production \
    up -d --build api web caddy'
```

For migration rollback, run `alembic downgrade -1` via the same
`compose run --rm` pattern deploy.sh uses.

## Backups (TODO)

Daily `pg_dump` + rsync `data/db` to R2. Cron not wired yet. Manual:

```bash
ssh doppler@62.238.7.125 'docker exec -t paczkomat-db pg_dump -U paczkomat \
  -d paczkomat_atlas -F c -f /tmp/dump.pgcustom && \
  docker cp paczkomat-db:/tmp/dump.pgcustom -' > /tmp/paczkomat-$(date -I).pgcustom
```

## Gotchas hit during first deploy

1. **`ports: []` doesn't clear inherited ports in compose**. Use `!reset
   []` for ports and volumes, `!override` for ports you want to replace.
2. **alembic in container needs `alembic.ini` + `alembic/`**. Original
   Dockerfile only copied `src/` — fixed in api/Dockerfile.
3. **pydantic-settings JSON-decodes list fields BEFORE validators run**.
   `CORS_ORIGINS=http://a,http://b` blew up until we wrapped the field as
   `Annotated[list[str], NoDecode]`.
4. **Next.js `pnpm build` pre-renders static pages**. The landing page
   fetches the API at build time → hangs because the API isn't running
   inside the builder. Fix: `export const dynamic = "force-dynamic"`.
5. **`NEXT_PUBLIC_*` env vars are inlined into the SERVER bundle at
   BUILD time**, not just the client bundle. Setting `NEXT_PUBLIC_API_
   BASE_URL=http://api:8000` at runtime did nothing — server fetches
   still went out to the public URL and looped back. Fix: separate
   `INTERNAL_API_BASE_URL` read at runtime.
6. **asyncpg can't infer bind type for `:param` in `ST_Transform(geom,
   :srid)`**. Hardcode constants in SQL or cast explicitly (`::integer`,
   but watch for SQLAlchemy's bind-name parser collision).
7. **doppler user has NO passwordless sudo**. Anything needing root
   (e.g., opening UFW ports) is on Niki. Docker port-binding bypasses
   UFW anyway, so this only matters for non-docker access.
8. **PRG load needs Docker CLI / docker.sock inside the api container**
   (it shells out to `docker run gdal/ogr2ogr`). Solved with a separate
   `prg-loader` compose service behind `profiles: ["loader"]`. See "PRG
   (gmina boundaries) ingest" above.
9. **Martin caches tiles per-process**. After bulk-loading data behind
   tile-source functions (gminy, lockers, etc.), `docker restart
   paczkomat-martin` — otherwise stale 204 responses linger until the
   process recycles. Caught when the gminy choropleth still rendered
   empty after the PRG load even though the SQL function returned
   1.1 MB of MVT bytes.

## Server recon snapshot (2026-05-15)

```
8 doppler containers running, all healthy
ports 80/443: FREE — own Caddy claims them
docker version 29.1.3, compose 2.40.3
RAM: 7.6 Gi total, ~3.9 Gi free
Disk: 75 Gi, 38 Gi free
swap: 4 Gi
no nginx/caddy systemd unit on host
existing docker networks: bridge, doppler_default, host, none
```

## Pre-deploy checklist (next time)

- [ ] Branch off main with the latest deploy/* changes merged.
- [ ] `./scripts/deploy.sh` from the dev laptop.
- [ ] If hostname / TLS change: edit `/home/doppler/paczkomat-atlas/.env.production`,
      then `docker compose ... up -d --build web caddy`.
- [ ] After first run, verify with:
  - `curl http://62.238.7.125/api/v1/health | jq` (or hostname after DNS)
  - `docker ps --filter name=paczkomat` — all healthy.
