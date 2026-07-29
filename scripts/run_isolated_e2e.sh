#!/bin/sh
set -eu

profile="${1:-}"
case "$profile" in
  default)
    export E2E_AGENTIC_ENABLED=false
    export E2E_AGENTIC_RAG_ENABLED=false
    export E2E_AGENT_RESEARCH_ENABLED=false
    ;;
  agentic)
    export E2E_AGENTIC_ENABLED=true
    export E2E_AGENTIC_RAG_ENABLED=true
    export E2E_AGENT_RESEARCH_ENABLED=true
    ;;
  phase2b)
    export E2E_AGENTIC_ENABLED=false
    export E2E_AGENTIC_RAG_ENABLED=false
    export E2E_AGENT_RESEARCH_ENABLED=false
    export E2E_PHASE2B_ENABLED=true
    ;;
  *)
    echo "usage: $0 {default|agentic|phase2b}" >&2
    exit 2
    ;;
esac

export E2E_FRONTEND_PORT="${E2E_FRONTEND_PORT:-23000}"
export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-28000}"
export E2E_POSTGRES_PORT="${E2E_POSTGRES_PORT:-25432}"
export E2E_REDIS_PORT="${E2E_REDIS_PORT:-26379}"
export E2E_MINIO_PORT="${E2E_MINIO_PORT:-29000}"
export E2E_MINIO_CONSOLE_PORT="${E2E_MINIO_CONSOLE_PORT:-29001}"
export E2E_BASE_URL="http://127.0.0.1:${E2E_FRONTEND_PORT}"
export E2E_API_BASE_URL="http://127.0.0.1:${E2E_BACKEND_PORT}/api/v1"
export E2E_BUILD_COMMIT="$(git rev-parse HEAD)"
export E2E_COMPATIBILITY_ID="ekip-e2e-v1"
export COMPOSE_PROJECT_NAME="ekip_e2e_${profile}_$$"

compose="docker compose -f docker-compose.yml -f docker-compose.e2e.yml"

cleanup() {
  $compose down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf frontend/test-results frontend/playwright-report
}
trap cleanup EXIT INT TERM

for port in "$E2E_FRONTEND_PORT" "$E2E_BACKEND_PORT" "$E2E_POSTGRES_PORT" \
  "$E2E_REDIS_PORT" "$E2E_MINIO_PORT" "$E2E_MINIO_CONSOLE_PORT"; do
  if nc -z 127.0.0.1 "$port" >/dev/null 2>&1; then
    echo "refusing to reuse occupied E2E port ${port}" >&2
    exit 3
  fi
done

$compose build backend frontend ingestion-worker
$compose up -d postgres redis minio minio-init backend frontend ingestion-worker \
  evaluation-worker report-worker

attempt=0
until curl --silent --fail "$E2E_API_BASE_URL/health/ready" >/dev/null &&
  curl --silent --fail "$E2E_BASE_URL/api/runtime-identity" >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 90 ]; then
    $compose ps
    $compose logs --no-color backend frontend
    exit 4
  fi
  sleep 1
done

node scripts/e2e_preflight.mjs
$compose run --rm backend alembic upgrade head
$compose run --rm backend alembic check

if [ "$profile" = "phase2b" ]; then
  (
    cd frontend
    npx playwright test tests/e2e/phase2b-browser.spec.ts --project=chromium
  )
else
  (
    cd frontend
    npm run test:e2e
  )
fi
