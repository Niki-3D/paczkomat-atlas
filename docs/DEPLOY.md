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

GitHub Actions `deploy.yml`:
1. Build `api` image, push to GHCR.
2. SSH to server, `docker compose pull && docker compose up -d`.
3. Run pending Alembic migrations.

Web auto-deploys to Cloudflare Pages on push to `main` via Cloudflare's GitHub integration.

## Backups

`pg_dump` daily → R2. Retain 14 days.

## TODO

- [ ] Wire up GHCR push in `deploy.yml`
- [ ] Backup cron
- [ ] Monitoring (Uptime Kuma on same host? or external)
- [ ] DNS + Cloudflare proxy config
