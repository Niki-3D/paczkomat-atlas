# Git Conventions

## Branches

- `main` — production, deploys via GitHub Actions on push
- `feat/<scope>-<thing>` — feature (e.g. `feat/ingest-inpost-client`)
- `fix/<scope>-<thing>` — bug fix
- `infra/<thing>` — Docker, CI/CD, Terraform, deployment
- `data/<thing>` — data pipelines, migrations, schema work
- `docs/<thing>` — docs-only changes
- `chore/<thing>` — tooling, config, deps

Branches live max 1–3 days. Long-lived branches rebase onto main daily.

## Commits — one logical change = one commit

NEVER bundle unrelated changes. If you touched two domains, that's two commits. If a "small fix" snuck in alongside a feature, split it via `git add -p`.

Format: `type(scope): description` — lowercase, imperative, ≤72 chars, no period.

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`, `infra`, `data`, `style`, `perf`.

Scopes for this project: `web`, `api`, `ingest`, `db`, `map`, `charts`, `landing`, `kpi`, `infra`, `claude`, `deps`, `compose`.

Good:
- `feat(ingest): add InPost API client with pagination`
- `fix(map): use feature-state for hover instead of layer re-render`
- `chore(claude): cross-platform stop hook beep`
- `docs(readme): fix next.js version mention`

Bad:
- `update stuff` — vague
- `feat: add ingest client and fix tooltip and update readme` — three commits in one
- `WIP` / `wip` / `temp` — never on any branch you push

## Rules

- One commit must pass `ruff check` + `pnpm typecheck` after applying. No exceptions.
- No WIP commits pushed to remote.
- No commented-out code in commits — delete it, git remembers.
- Never commit: `.env`, secrets, data files (`*.parquet`, `*.pmtiles`, `*.shp`, `*.pbf`, `*.osm.pbf`), `*.tfvars`, anything in `data/`.
- Never `git push --force` to main. Force-push only your own feature branch, never shared.
- Migrations are append-only — never edit a shipped Alembic migration, create a new one.

## When unsure

- "Is this one logical change?" — if you can describe it without "and", yes.
- "Should this be its own commit?" — if reverting it alone leaves the codebase coherent, yes.
- "Can I squash later?" — yes, but write commits as if permanent. Don't lean on squash to mask sloppy work.

## PR / merge

- Single-dev mode: direct commits to main allowed for trivial chore/docs.
- Features/refactors: branch + PR even when self-merging — preserves history and reviewability.
- Squash-merge feature branches with messy history; merge-commit when commits are already clean.
- CI must pass before merge.

## Pre-push checklist (mental)

Before pushing, ask: did I bundle? did tests pass? did I leak `.env`? did I commit data files? If yes to any — fix before pushing, not after.
