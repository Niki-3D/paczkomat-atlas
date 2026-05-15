#!/usr/bin/env bash
# Push local data/raw/* to the server via scp + tar.
#
# Used once on initial deploy to seed the gitignored static data (PRG, GUS,
# Eurostat). After that, the server can refresh in place by re-running
# scripts/download_static_data.sh inside a container that has uv + curl.

set -euo pipefail

SERVER="${DEPLOY_SERVER:-doppler@62.238.7.125}"
REMOTE_DIR="${DEPLOY_DIR:-/home/doppler/paczkomat-atlas}"

echo "=== Pushing data/raw/* to $SERVER:$REMOTE_DIR/data/raw/ ==="
echo "  → measuring size..."
du -sh data/raw/

echo "  → streaming via tar over ssh..."
tar -czf - data/raw/ | ssh "$SERVER" "mkdir -p $REMOTE_DIR && cd $REMOTE_DIR && tar -xzf -"

echo ""
echo "=== Verify on server ==="
ssh "$SERVER" "du -sh $REMOTE_DIR/data/raw/* && ls $REMOTE_DIR/data/raw/prg/"
