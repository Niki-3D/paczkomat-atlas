# Paczkomat Atlas

> InPost parcel locker network analytics — Polish gmina detail + European NUTS-2 overview. Built for the InPost Technology Internship 2026 submission.

🗺️  **Live:** _(coming soon)_

## What

InPost has **~154,000** pickup points across 14 European countries — 27k machines in Poland (network saturated, slow growth) and growing rapidly abroad (France just overtook Poland in machines). This dashboard surfaces:

- Coverage gaps: lockers per 10k inhabitants per gmina (PL) and NUTS-2 region (EU)
- Network mix: parcel lockers vs PUDO points
- Operational characteristics: 24/7 availability, accessibility, physical types
- Expansion velocity: country-level deployment trajectory

The goal is the analysis InPost's network planning team could plausibly run internally.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 · React 19 · TypeScript · Tailwind v4 · shadcn/ui · MapLibre GL JS |
| Backend | FastAPI · SQLAlchemy 2.0 async · Polars · Pydantic v2 |
| Database | PostgreSQL 16 + PostGIS 3.5 |
| Tiles | Protomaps PMTiles (self-hosted on Cloudflare R2) |
| Infra | Docker Compose · Caddy · Hetzner CX22 · GitHub Actions · Terraform |

## Run locally

```bash
cp .env.example .env
docker compose -f infra/compose/docker-compose.yml up -d db
cd api && uv sync && uv run fastapi dev
cd ../web && pnpm install && pnpm dev
```

## Architecture

See `docs/ARCHITECTURE.md` for module breakdown and `docs/DATA_MODEL.md` for the PostGIS schema.

## Recon

Exploratory phase (API quirks, data quality findings, auxiliary sources) under `docs/recon/`.

## Deploy

See `docs/DEPLOY.md`. Hetzner-based, ~4€/month, fully scripted.

## License

MIT
