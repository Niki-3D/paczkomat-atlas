#!/usr/bin/env bash
set -euo pipefail
FILE_PATH="${FILE_PATH:-${CLAUDE_FILE_PATH:-}}"
[ -z "$FILE_PATH" ] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

case "$FILE_PATH" in
  *.py)
    if command -v ruff &>/dev/null; then
      ruff check --fix "$FILE_PATH" 2>/dev/null || true
      ruff format "$FILE_PATH" 2>/dev/null || true
    fi
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.mjs|*.cjs|*.json|*.md|*.css)
    if [ -f "web/package.json" ] && command -v pnpm &>/dev/null; then
      (cd web && pnpm exec prettier --write "$FILE_PATH" 2>/dev/null || true)
    fi
    ;;
esac
exit 0
