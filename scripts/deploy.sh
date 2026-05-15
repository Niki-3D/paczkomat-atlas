#!/usr/bin/env bash
# Deploy paczkomat-atlas to the production server.
#
# Idempotent: safe to re-run. First run sets up everything; later runs sync
# code, rebuild images, apply new migrations.
#
# Code sync uses git on the server (rsync not portable from Windows). The
# server clones from origin and checks out whatever branch you pass with
# --branch (default: the branch you're currently on locally).
#
# Data sync (data/raw/*) is a separate concern — those files are gitignored.
# Use scripts/deploy_data.sh once to push them via scp; afterwards the
# server keeps its copy.
#
# Flags:
#   --branch <name>  Branch to deploy. Default: current local branch.
#   --skip-build     Skip docker build (use existing images on server).
#   --skip-migrate   Skip alembic upgrade.
#
# Env overrides:
#   DEPLOY_SERVER    Default: doppler@62.238.7.125
#   DEPLOY_DIR       Default: /home/doppler/paczkomat-atlas
#   GIT_REMOTE       Default: https://github.com/Niki-3D/paczkomat-atlas.git

set -euo pipefail

SERVER="${DEPLOY_SERVER:-doppler@62.238.7.125}"
REMOTE_DIR="${DEPLOY_DIR:-/home/doppler/paczkomat-atlas}"
GIT_REMOTE="${GIT_REMOTE:-https://github.com/Niki-3D/paczkomat-atlas.git}"
COMPOSE_PROJECT="paczkomat"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
SKIP_BUILD=0
SKIP_MIGRATE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --branch)      BRANCH="$2"; shift 2 ;;
        --skip-build)  SKIP_BUILD=1; shift ;;
        --skip-migrate) SKIP_MIGRATE=1; shift ;;
        *) echo "Unknown flag: $1"; exit 2 ;;
    esac
done

echo "=== Deploying $BRANCH to $SERVER:$REMOTE_DIR ==="

# -- 1. Local sanity --
echo "[1/9] Verifying local state..."
LOCAL_SHA="$(git rev-parse HEAD)"
echo "  → local branch=$BRANCH sha=$LOCAL_SHA"

# -- 2. SSH check --
echo "[2/9] Checking SSH..."
ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER" "echo SSH_OK" >/dev/null

# -- 3. Clone or fetch on the server --
echo "[3/9] Syncing code via git..."
ssh "$SERVER" bash -s <<REMOTE
set -euo pipefail
if [ ! -d "$REMOTE_DIR/.git" ]; then
    echo "  → cloning $GIT_REMOTE → $REMOTE_DIR"
    git clone "$GIT_REMOTE" "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"
git fetch --quiet origin "$BRANCH"
git checkout --quiet "$BRANCH"
git reset --hard "origin/$BRANCH"
echo "  → server now at \$(git rev-parse --short HEAD) on $BRANCH"
mkdir -p data/db data/raw/prg data/raw/eurostat data/raw/gus
REMOTE

# -- 4. .env.production: generate on first deploy --
echo "[4/9] Checking server .env.production..."
ssh "$SERVER" bash -s <<REMOTE
set -euo pipefail
cd "$REMOTE_DIR"
if [ ! -f .env.production ]; then
    echo "  → no .env.production found — generating with fresh passwords"
    cp infra/compose/.env.production.example .env.production
    POSTGRES_PASS=\$(openssl rand -base64 32 | tr -d '/+=\n' | head -c 32)
    APP_PASS=\$(openssl rand -base64 32 | tr -d '/+=\n' | head -c 32)
    sed -i "s|GENERATE_AT_DEPLOY_POSTGRES_PASSWORD|\$POSTGRES_PASS|" .env.production
    sed -i "s|GENERATE_AT_DEPLOY_APP_PASSWORD|\$APP_PASS|" .env.production
    chmod 600 .env.production
    echo "  → wrote .env.production (0600). REVIEW the non-secret values:"
    echo "    PUBLIC_HOSTNAME, NEXT_PUBLIC_API_BASE_URL, CORS_ORIGINS, TLS_EMAIL"
else
    echo "  → .env.production already exists, leaving untouched"
fi
REMOTE

# -- 5. Build images --
if [ "$SKIP_BUILD" -eq 1 ]; then
    echo "[5/9] Skipping build (--skip-build)"
else
    echo "[5/9] Building images on server..."
    ssh "$SERVER" "cd $REMOTE_DIR && docker compose -p $COMPOSE_PROJECT \
        -f infra/compose/docker-compose.yml \
        -f infra/compose/docker-compose.prod.yml \
        --env-file .env.production \
        build api web caddy"
fi

# -- 6. Start db + wait healthy --
echo "[6/9] Starting db..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose -p $COMPOSE_PROJECT \
    -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml \
    --env-file .env.production \
    up -d db"

echo "  → waiting for db healthcheck..."
ssh "$SERVER" 'for i in $(seq 1 30); do
    status=$(docker inspect -f "{{.State.Health.Status}}" paczkomat-db 2>/dev/null || echo starting)
    if [ "$status" = healthy ]; then echo "  → db healthy"; exit 0; fi
    sleep 2
done; echo "  → db did not become healthy in 60s"; exit 1'

# -- 7. Run migrations (direct :5432, admin role) --
if [ "$SKIP_MIGRATE" -eq 1 ]; then
    echo "[7/9] Skipping migrations (--skip-migrate)"
else
    echo "[7/9] Applying migrations (direct DB, admin role)..."
    ssh "$SERVER" bash -s <<REMOTE
set -euo pipefail
cd "$REMOTE_DIR"
set -a; . ./.env.production; set +a
docker compose -p $COMPOSE_PROJECT \
    -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml \
    --env-file .env.production \
    run --rm --no-deps \
    -e DATABASE_URL="postgresql+asyncpg://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@db:5432/\${POSTGRES_DB}" \
    api alembic upgrade head
REMOTE
fi

# -- 8. Set the app-role password every time --
echo "[8/9] Setting paczkomat_app role password..."
ssh "$SERVER" bash -s <<REMOTE
set -euo pipefail
cd "$REMOTE_DIR"
set -a; . ./.env.production; set +a
docker compose -p $COMPOSE_PROJECT \
    -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml \
    --env-file .env.production \
    exec -T db psql -U "\$POSTGRES_USER" -d "\$POSTGRES_DB" \
    -c "ALTER ROLE paczkomat_app WITH LOGIN PASSWORD '\$POSTGRES_APP_PASSWORD'" \
    > /dev/null
echo "  → app role password rotated to match .env.production"
REMOTE

# -- 9. Bring the full stack up --
echo "[9/9] Starting full stack..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose -p $COMPOSE_PROJECT \
    -f infra/compose/docker-compose.yml \
    -f infra/compose/docker-compose.prod.yml \
    --env-file .env.production \
    up -d"

echo ""
echo "=== Deploy complete ==="
echo ""
echo "Verify:"
echo "  ssh $SERVER 'docker ps --filter name=paczkomat'"
echo "  ssh $SERVER 'docker logs paczkomat-caddy --tail 30'"
