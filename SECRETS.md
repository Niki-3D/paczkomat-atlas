# Secrets and Environment Variables

All configuration is supplied via environment variables. `.env` is gitignored;
`.env.example` is the public template with safe placeholders. No secret has
ever been committed to this repo (verified via `git log --all --full-history`).

## Required variables

| Variable | Required | Sensitive | Default | Description |
|---|---|---|---|---|
| `POSTGRES_USER` | yes | low | `paczkomat` | Postgres superuser (dev) / admin (prod) |
| `POSTGRES_PASSWORD` | yes | **HIGH** | none | Postgres admin password — generate with `openssl rand -base64 32` for prod |
| `POSTGRES_DB` | yes | no | `paczkomat_atlas` | Database name |
| `POSTGRES_HOST` | yes | no | `localhost` | DB host (compose: `db`) |
| `POSTGRES_PORT` | yes | no | `5432` | Direct DB port (Alembic) |
| `POSTGRES_APP_PASSWORD` | prod | **HIGH** | none | Password for the `paczkomat_app` least-privilege role — see `docs/DEPLOY.md` |
| `DATABASE_URL` | yes | **HIGH** | see `.env.example` | SQLAlchemy async URL. Dev points at `:5432` (direct). Prod points at `pgbouncer:5432` with the `paczkomat_app` role. |
| `LOG_LEVEL` | no | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `CORS_ORIGINS` | prod | no | `http://localhost:3000` | Comma-separated allowed origins for the public API |
| `INPOST_API_URL` | no | no | upstream URL | Override only for testing |
| `BDL_API_KEY` | no (ingest only) | **MEDIUM** | none | GUS BDL API key — needed only when running population ingest |
| `EUROSTAT_API_URL` | no | no | upstream URL | Override only for testing |
| `CONTEXT7_API_KEY` | dev only | **MEDIUM** | none | Claude Code MCP — never set in prod |
| `NEXT_PUBLIC_API_BASE_URL` | yes | **public-safe** | `http://localhost:8080` | Frontend → API origin. `NEXT_PUBLIC_*` is **embedded in the browser bundle**; never put a secret behind this prefix. |
| `NEXT_PUBLIC_TILES_URL` | no | **public-safe** | none | PMTiles URL (legacy — Martin now serves vector tiles) |
| `MARTIN_HEALTH_URL` | no | no | `http://martin:3000/health` | Internal health probe — compose service name |

## Public-safe vs server-only

- `NEXT_PUBLIC_*` is exposed in the browser bundle by Next.js. Anything here is
  effectively public. Use only for URLs and feature flags.
- All other variables are server-only and must never be re-exported with the
  `NEXT_PUBLIC_` prefix.

## Production deployment

1. Generate strong passwords:
   ```bash
   openssl rand -base64 32  # POSTGRES_PASSWORD
   openssl rand -base64 32  # POSTGRES_APP_PASSWORD
   ```
2. Set `CORS_ORIGINS` to the exact production hostname (no wildcards).
3. After first `alembic upgrade head`, rotate the `paczkomat_app` role password —
   see `docs/DEPLOY.md`.
4. Confirm the production `DATABASE_URL` uses the `paczkomat_app` role, not the
   admin role, and points at `pgbouncer:5432`.

## Verification

```bash
# Confirm no .env file has ever been committed
git log --all --full-history -- .env '.env.*'
# Confirm gitignore covers
grep -E '\.env' .gitignore
```
