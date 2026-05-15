# Deploy

> Single-server Hetzner deployment. Target ~4€/month.

## Topology

- 1× Hetzner CX22 (2 vCPU, 4 GB RAM, 40 GB disk) in `fsn1`
- Docker Compose: `db` + `api` + `caddy`
- Caddy terminates TLS via Let's Encrypt
- Web (static export) served from Cloudflare Pages
- PMTiles + raw geo artifacts in Cloudflare R2

## One-time provisioning

1. `cd infra/terraform && terraform init && terraform apply`
2. Note the `server_ip` output.
3. SSH in, install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   usermod -aG docker $USER
   ```
4. Clone repo, copy `.env`, mount data volumes at `/opt/paczkomat/`.

## Deploys

`.github/workflows/deploy.yml` is currently a placeholder. Until the SSH-deploy
workflow is wired up (TODO below), deploys are manual. The runbook:

### Manual deploy runbook (run from your laptop)

```bash
# 1. Pre-flight: confirm CI is green on the commit you're shipping
gh run list --branch main --limit 1
# expect status=completed, conclusion=success

# 2. SSH in
ssh paczkomat@<server_ip>
cd /opt/paczkomat

# 3. Fetch the new revision (deploys track main)
git fetch origin
git reset --hard origin/main

# 4. Rebuild the api image (web is built+served separately via Cloudflare Pages
#    OR, if served from the same host, rebuild the web image too)
docker compose -f infra/compose/docker-compose.yml --env-file .env build api

# 5. Bring services up in dependency order — db must be healthy before api
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d db pgbouncer
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d martin
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d api caddy

# 6. Run pending Alembic migrations AGAINST THE DIRECT DB PORT (5432), not
#    pgbouncer. Migrations need transactional DDL + advisory locks that the
#    transaction-mode pool breaks. The api container has its env_file pointed
#    at the direct connection — re-using that exec keeps the surface honest.
docker compose -f infra/compose/docker-compose.yml --env-file .env exec api alembic upgrade head

# 7. Smoke check
curl -s https://<domain>/api/v1/health | jq
# expect db_ok=true, martin_ok=true, locker_count > 100000

# 8. Tail logs for the first 60s in case something paged
docker compose -f infra/compose/docker-compose.yml --env-file .env logs -f --since=2m api caddy
```

### Rollback

```bash
# Same shape, just point at the previous commit hash
git reset --hard <previous-sha>
docker compose -f infra/compose/docker-compose.yml --env-file .env build api
docker compose -f infra/compose/docker-compose.yml --env-file .env up -d api
# Migrations: only roll back if the previous revision needs an earlier head.
# `alembic downgrade -1` is reversible for everything in this repo today.
```

Web auto-deploys to Cloudflare Pages on push to `main` via Cloudflare's GitHub integration.

## Production compose override

The base `docker-compose.yml` is configured for local dev — it publishes db,
pgbouncer, martin, and api ports to the host so you can attach `psql` or hit
`/api/v1/*` directly. **In production those ports must not be reachable from
the public internet.** Use the override file to lock everything except Caddy:

```bash
docker compose \
  -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.prod.yml \
  --env-file .env up -d
```

Verify only Caddy publishes host ports:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config \
  | grep published
# Expect: caddy 80, caddy 443. Nothing else.
```

## First-time DB role setup on prod

After `alembic upgrade head` runs on production:

1. Generate a strong password:
   ```bash
   openssl rand -base64 32
   ```
2. Rotate the placeholder password the migration set:
   ```bash
   docker exec paczkomat-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -c "ALTER ROLE paczkomat_app PASSWORD '<password>';"
   ```
3. Put the value in production `.env` as `POSTGRES_APP_PASSWORD`.
4. Switch the API's `DATABASE_URL` over to the `paczkomat_app` role:
   ```
   DATABASE_URL=postgresql+asyncpg://paczkomat_app:${POSTGRES_APP_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}
   ```
5. Restart so the api picks up the new connection string:
   ```bash
   docker compose ... restart api
   ```
6. Sanity-check the role's privileges:
   ```bash
   docker exec paczkomat-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\du paczkomat_app"
   # Expect: no Superuser, no Create role, no Create DB.
   ```

The migration leaves the placeholder password in place so a fresh dev DB
also gets the role (handy for testing prod connection strings locally).
Production deploys MUST rotate it before the API connects with the role.

## Backups

`pg_dump` daily → R2. Retain 14 days.

## TODO

- [ ] Wire up GHCR push in `deploy.yml`
- [ ] Backup cron
- [ ] Monitoring (Uptime Kuma on same host? or external)
- [ ] DNS + Cloudflare proxy config
