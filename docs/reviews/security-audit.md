# Pre-deploy security audit

Date: 2026-05-15
Branch: `chore/pre-deploy-security` off `feat/frontend-dashboard`
Scope: harden the codebase before the dashboard goes on a public hostname.

Goal: a random visitor (recruiter, bot, drive-by scanner) can read public
endpoints but cannot read the DB, cannot modify state, and cannot crash the
service into a state that leaks internal information.

## Summary by area

| # | Area | Status | Key finding |
|---|---|---|---|
| 1 | Secrets & credentials | pass | No secrets ever committed. Fixed env var name mismatch (NEXT_PUBLIC_API_URL → NEXT_PUBLIC_API_BASE_URL). |
| 2 | DB / service exposure | fixed | Previous prod override left pgbouncer (6432), martin (3001), api (8000), and caddy (8080) bound to the host. `ports: []` doesn't work as a compose merge — switched to `!reset []` and `!override`. |
| 3 | DB user privileges | fixed | Created Alembic revision adding `paczkomat_app` least-privilege role. Prod deploy must rotate the placeholder password and switch DATABASE_URL. |
| 4 | HTTP security | fixed | Replaced `allow_origins=["*"]` with env-driven `CORS_ORIGINS`. Added X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS, CSP, Permissions-Policy in Caddy. Rate-limit wiring deferred — needs xcaddy rebuild. |
| 5 | Dependency CVEs | fixed | Python clean (0 vulnerable). JS had 1 moderate (postcss <8.5.10 transitive); pinned via pnpm override. |
| 6 | Input validation | fixed | Added regex `[A-Za-z]{2}` to every country param, length caps on free-text params (status, voivodeship, locker name), pattern guard on locker name. |
| 7 | Logging hygiene | fixed | Added structlog `redact_sensitive` processor. 6 unit tests. |
| 8 | Error response leakage | fixed | Added global exception handler — sanitized 500 body with request_id, full traceback only in server logs. |
| 9 | Frontend XSS | pass | Zero `dangerouslySetInnerHTML`, `innerHTML`, `outerHTML`, `document.write`, `eval`, or `new Function`. All hrefs use static strings. React default escaping holds. |

No critical findings. No secret leaks. Audit branch is safe to push publicly.

## Detail

### Area 1 — Secrets & credentials

- `git log --all --full-history -- .env '.env.*'` returns no commits.
- Repo-wide grep for `api[_-]?key|secret|password|token|bearer` matched only:
  - `.env.example` placeholders (`changeme_local_only`, `BDL_API_KEY=`).
  - `infra/terraform/README.md`: a literal `"your-token-here"` placeholder.
- `.gitignore` covers `.env`, `.env.*`, `**/secrets/`, `*.tfvars`, data files.
- `.env.example` had `NEXT_PUBLIC_API_URL` but code reads
  `NEXT_PUBLIC_API_BASE_URL`. Fixed.
- `SECRETS.md` at repo root documents every variable, marks each sensitive
  or public-safe, and explains `NEXT_PUBLIC_*` bundle-embedding semantics.

### Area 2 — DB / service exposure

- Dev `docker-compose.yml` publishes 5 ports to the host (5432, 6432, 3001,
  8000, 8080) by design — local dev needs them.
- Pre-audit `docker-compose.prod.yml` only cleared `db.ports` and `api.ports`.
  pgbouncer, martin, and caddy:8080 stayed bound to the host. Verified with
  `docker compose ... config | grep published`.
- `ports: []` does not remove inherited entries in compose v2 (list merge,
  not list replace). Switched to:
  - `ports: !reset []` on db, pgbouncer, martin, api.
  - `ports: !override` on caddy to replace :8080 with 80/443.
- Added `expose:` blocks to document the internal port each service listens on.
- Post-fix `compose config` output: only `caddy 80` and `caddy 443` published.

### Area 3 — DB user privileges

- Current dev DB uses one role (`paczkomat`) with full superuser-like access
  on the cluster. Acceptable for dev; not for prod.
- New Alembic migration `72d896bb1f4e_add_app_role_with_least_privilege`:
  - Creates `paczkomat_app` role with LOGIN.
  - GRANT SELECT on all tables, sequences, and MVs in schema public.
  - GRANT INSERT/UPDATE/DELETE on the 6 ingest target tables only.
  - GRANT EXECUTE on Martin's three tile-source functions.
  - DEFAULT PRIVILEGES grants SELECT on future tables (no write — those must
    be granted explicitly each time the schema grows).
  - Idempotent (`DO ... IF NOT EXISTS`).
  - Downgrade: `DROP OWNED CASCADE` + `DROP ROLE IF EXISTS`.
- Migration was not applied locally (DB not running during audit).
- `docs/DEPLOY.md` now has a "First-time DB role setup on prod" section with
  the password-rotation steps + DATABASE_URL switch.

### Area 4 — HTTP security

CORS:
- `Settings.cors_origins` (default `["http://localhost:3000", "http://localhost:8080"]`).
- `field_validator` parses comma-separated string from env.
- `CORSMiddleware(allow_origins=settings.cors_origins, allow_methods=["GET","OPTIONS"], max_age=3600)`.
- Production must set `CORS_ORIGINS` to the exact public hostname; `*` would
  pass the validator but bypass the protection — flagged in SECRETS.md.

Caddy security headers (every response, dev + prod):
- `-Server` removes the Caddy version line.
- `X-Content-Type-Options: nosniff`.
- `X-Frame-Options: DENY` (no iframe embedding).
- `Referrer-Policy: strict-origin-when-cross-origin`.
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`.
- `Content-Security-Policy: default-src 'self'; ...` (scoped to self + CartoCDN
  + OpenFreeMap, with `blob:` + `unsafe-inline` + `unsafe-eval` for Next.js
  and MapLibre worker). `frame-ancestors 'none'`.
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`.

Rate limiting:
- `caddy:2.8-alpine` doesn't include the rate-limit module. Wiring is in the
  Caddyfile as commented directives; enabling needs an xcaddy rebuild with
  `mholt/caddy-ratelimit`. Deferred to a follow-up to keep this PR scoped to
  changes that don't require a new image build.

### Area 5 — Dependency CVEs

Python:
- `uv export | pip-audit` on 69 packages: **no known vulnerabilities**.

JavaScript:
- `pnpm audit`: 1 moderate (postcss <8.5.10, GHSA-qx2v-qp2m-jg93 XSS in CSS
  stringify path). Below the high/critical threshold but trivially fixable.
- Added `pnpm.overrides` pin: `"postcss@<8.5.10": ">=8.5.10"`.
- Re-audit: clean. Typecheck passes against the bumped version.

### Area 6 — Input validation

Walked all 7 routers. Updates:

| File | Param | Before | After |
|---|---|---|---|
| locker.py | `country` Query | `min=2,max=2` | + `pattern=^[A-Za-z]{2}$` |
| locker.py | `status` Query | unbounded | `max_length=32, pattern=^[A-Za-z]+$` |
| locker.py | `name` Path | unbounded | `min=1, max=64, pattern=^[A-Za-z0-9_\-]+$` |
| kpi.py | `country` Path | unbounded | `min=2, max=2, pattern=^[A-Za-z]{2}$` |
| density.py | `country` Query | `min=2,max=2` | + pattern |
| density.py | `voivodeship` Query | unbounded | `max_length=64` (no ASCII pattern — Polish chars) |
| h3.py | `country` Query | `min=2,max=2` | + pattern |
| velocity.py | `country` Query | `min=2,max=2` | + pattern |

All numeric Query params already had `ge=` / `le=` bounds.

### Area 7 — Logging hygiene

- Added `redact_sensitive` structlog processor matching the regex
  `(password|passwd|pwd|secret|token|bearer|api[_-]?key)\s*[:=]\s*([^\s"'&]+)`
  in any string value of the event dict. Inserted just before the renderer.
- 6 unit tests cover the main shapes (DSN, bearer, query-string, dash/underscore
  variants, passthrough, non-string values). All pass.
- Audit did NOT find any existing log line that actually emits a credential,
  but `ingest/prg_loader.py` builds an ogr2ogr command containing the DB
  password as a string — if a future change ever logs that string, the
  processor catches it.

### Area 8 — Error response leakage

- No `debug=True` set anywhere in config.
- Added `@app.exception_handler(Exception)` returning:
  ```json
  {"errors":[{"code":"internal_server_error","message":"Internal server error"}],
   "request_id":"<x-request-id>"}
  ```
  with status 500. No traceback, no exception class name, no SQL text in the
  client response. Full traceback goes through structlog (and through
  `redact_sensitive`).

### Area 9 — Frontend XSS

- `dangerouslySetInnerHTML`: 0 occurrences.
- `innerHTML`, `outerHTML`, `document.write`: 0 occurrences.
- `eval(`, `new Function(`: 0 occurrences.
- `href={...}` and `src={...}`: only one match (footer link with static
  prop). All other URLs are either string literals or come from
  `web/lib/api.ts` (server-controlled).
- React's default JSX `{value}` escaping is the only path user-controllable
  strings reach the DOM. Default escaping handles XSS for everything covered.

## Deferred / follow-ups

- **Caddy rate limit**: needs an xcaddy rebuild with `mholt/caddy-ratelimit`
  to enable. Wiring is in the Caddyfile, commented. Track in a follow-up so
  this PR can ship with a stock `caddy:2-alpine` image.
- **Apply Alembic migration `72d896bb1f4e` against staging/prod** before the
  first prod deploy — the audit environment didn't have a running DB.
- **Run an integration smoke test of the prod compose stack** (`docker compose
  -f docker-compose.yml -f docker-compose.prod.yml up -d`) on the Hetzner VM
  to confirm the merged config actually starts and Caddy routes everything
  via the internal docker network.

## Pre-deploy checklist (for Nikodem to verify on the live server)

- [ ] `.env` on the server has unique values for `POSTGRES_PASSWORD`
      and `POSTGRES_APP_PASSWORD` (`openssl rand -base64 32`).
- [ ] `.env` `CORS_ORIGINS=https://<your-domain>` (no `*`).
- [ ] `.env` `DATABASE_URL` for the api container uses the `paczkomat_app`
      role + pgbouncer:5432.
- [ ] Bring up with both compose files:
      `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.
- [ ] `docker compose ... config | grep published` returns ONLY caddy 80 and
      caddy 443.
- [ ] `alembic upgrade head` brings DB to `72d896bb1f4e`.
- [ ] Run the password rotation steps in `docs/DEPLOY.md`
      ("First-time DB role setup on prod").
- [ ] `\du paczkomat_app` in psql shows: no Superuser, no Create role,
      no Create DB.
- [ ] From the public internet, `nc -zv <host> 5432 6432 3001 8000 8080`
      all refuse connection. Only 80 and 443 connect.
- [ ] `curl -I https://<host>/api/v1/health` returns the security headers.
- [ ] `curl https://<host>/api/v1/nonexistent` returns 404 with the sanitized
      error envelope (no traceback).
- [ ] `curl -H "Origin: https://attacker.example" https://<host>/api/v1/health`
      does NOT include `Access-Control-Allow-Origin` for that origin.
