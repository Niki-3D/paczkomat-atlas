#!/usr/bin/env bash
set -euo pipefail
echo "→ Checking tooling..."
for tool in node pnpm uv docker; do
  command -v "$tool" >/dev/null || { echo "✗ Missing: $tool"; exit 1; }
done
echo "→ Copying .env.example to .env (if missing)..."
[ ! -f .env ] && cp .env.example .env
echo "→ Installing web deps..."
(cd web && pnpm install)
echo "→ Syncing api deps..."
(cd api && uv sync --all-extras)
echo "→ Making Claude hooks executable..."
chmod +x .claude/hooks/*.sh
echo "✓ Done. Next: docker compose -f infra/compose/docker-compose.yml up -d db"
