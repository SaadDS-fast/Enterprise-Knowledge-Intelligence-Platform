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
  ollama)
    export E2E_AGENTIC_ENABLED=false
    export E2E_AGENTIC_RAG_ENABLED=false
    export E2E_AGENT_RESEARCH_ENABLED=false
    export E2E_LOCAL_LLM_BACKEND=ollama
    export E2E_OLLAMA_ENABLED=true
    export E2E_LOCAL_LLM_BASE_URL=http://host.docker.internal:11434
    export E2E_LOCAL_LLM_MODEL=llama3:latest
    export E2E_OLLAMA_ALLOWED_MODELS=llama3:latest
    export E2E_OLLAMA_ENABLED=true
    ;;
  enterprise)
    export E2E_AGENTIC_ENABLED=true
    export E2E_AGENTIC_RAG_ENABLED=true
    export E2E_AGENT_RESEARCH_ENABLED=true
    export E2E_ENTERPRISE_ENABLED=true
    ;;
  *)
    echo "usage: $0 {default|agentic|phase2b|ollama|enterprise}" >&2
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
elif [ "$profile" = "ollama" ]; then
  (
    cd frontend
    npx playwright test tests/e2e/ollama-grounded.spec.ts --project=chromium --workers=1
  )
elif [ "$profile" = "enterprise" ]; then
  runtime_result="$(mktemp -t ekip-enterprise-result.XXXXXX)"
  python3 scripts/enterprise_acceptance.py \
    --base-url "$E2E_API_BASE_URL" --upload-workers 4 --output "$runtime_result"
  cp "$runtime_result" "${E2E_ENTERPRISE_RESULT_PATH:-/tmp/ekip-enterprise-result.json}"
  rm -f "$runtime_result"
  python3 scripts/enterprise_load.py --base-url "$E2E_API_BASE_URL" \
    --duration-seconds "${E2E_ENTERPRISE_LOAD_SECONDS:-120}" \
    > "${E2E_ENTERPRISE_LOAD_RESULT_PATH:-/tmp/ekip-enterprise-load.json}"
  if [ "${E2E_ENTERPRISE_SOAK_SECONDS:-0}" -gt 0 ]; then
    python3 scripts/enterprise_load.py --base-url "$E2E_API_BASE_URL" \
      --duration-seconds "$E2E_ENTERPRISE_SOAK_SECONDS" --health-clients 2 --search-clients 1 \
      > "${E2E_ENTERPRISE_SOAK_RESULT_PATH:-/tmp/ekip-enterprise-soak.json}"
  fi
  E2E_COMPOSE_FILES="-f docker-compose.yml -f docker-compose.e2e.yml" \
    scripts/validate_backup_restore.sh \
    > "${E2E_ENTERPRISE_BACKUP_RESULT_PATH:-/tmp/ekip-enterprise-backup.json}"
  if [ "${E2E_ENTERPRISE_OPERATIONAL:-false}" = "true" ]; then
    EKIP_COMPOSE_FILES="-f docker-compose.yml -f docker-compose.e2e.yml" \
      backend/.venv/bin/python scripts/operational_validation.py --base-url "$E2E_API_BASE_URL" \
      --output "${E2E_ENTERPRISE_OPERATIONAL_RESULT_PATH:-/tmp/ekip-enterprise-operational.json}"
    python3 scripts/local_agentic_load.py --base-url "$E2E_API_BASE_URL" \
      --users 5 --requests-per-user 2 \
      > "${E2E_ENTERPRISE_AGENT_LOAD_RESULT_PATH:-/tmp/ekip-enterprise-agent-load.json}"
  fi
  (
    cd frontend
    npx playwright test tests/e2e/enterprise-release.spec.ts --project=chromium --workers=1
  )
else
  (
    cd frontend
    npm run test:e2e
  )
fi
