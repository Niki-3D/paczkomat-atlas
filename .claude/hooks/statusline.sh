#!/usr/bin/env bash
BRANCH=$(git branch --show-current 2>/dev/null || echo "no-git")
DIRTY=""
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
  DIRTY="*"
fi
echo "🗺️  paczkomat-atlas │ ${BRANCH}${DIRTY}"
