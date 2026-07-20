# Validation Report

Validated on 2026-07-20 on branch `fix/runtime-reliability-and-e2e`.

## Environment

- Current HEAD: `5f7846703dcd7f0ee8bc5a9d6bfd13a54ca12dd2`
- Source branch resumed from: `validation/full-runtime-stack`
- Working tree: contains uncommitted validation/runtime changes
- Python: 3.12.13
- Node: v20.20.2
- npm: 10.8.2
- Docker: 29.6.2
- Docker Compose: v5.3.1

## Overall Status

**PASS**

The Dockerized runtime stack passed validation for backend, frontend, PostgreSQL/pgvector, Redis/Celery, MinIO, Prometheus worker scraping, and browser E2E. Ollama profile and load testing remain out of scope for this pass and are documented as follow-up items, not blockers for the requested runtime reliability fixes.

## Key Runtime Results

- Completed-task retry: **PASS**. A duplicate Celery task for completed job `b1f52514-8a77-489b-afc7-40a90f6d9ae3` returned successfully, preserved request id `a99f349a-631a-4089-9a44-62093233da46`, and kept counts at 1 chunk / 1 embedded chunk. Targeted logs had no asyncpg or event-loop warnings.
- Redis outage recovery: **PASS**. Upload while Redis was stopped returned 202 with job `54a2de89-f572-4f83-91f3-c8cc22247702` marked `retry_pending`; after Redis restart the backend dispatcher automatically published it and the job completed. Database check showed 0 jobs stuck in `retry_pending` or `dispatch_failed`.
- MinIO outage safety: **PASS**. Upload while MinIO was stopped returned sanitized 500 and document count stayed 0 for that workspace.
- Worker metrics: **PASS**. Prometheus targets for `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103`, and `backend:8000` all reported `up=1`. `ekip_worker_tasks_completed_total{worker_role="ingestion"}` reached 4 after runtime probes.
- Browser E2E: **PASS**. Playwright Chromium ran against Dockerized frontend/backend: 1 spec passed covering register, login, upload, ingestion, search evidence, abstention, tenant isolation, logout, and cleanup.

## Commands Run

- `docker compose config`
- `docker compose build`
- `docker compose build backend`
- `docker compose --profile observability up -d`
- `docker compose run --rm backend alembic check`
- `docker compose --profile observability ps`
- Prometheus API queries for `up` and worker completion metrics
- Live API probes for upload, retry, Redis outage recovery, and MinIO outage safety
- `backend/.venv/bin/python -m compileall app tests`
- `backend/.venv/bin/ruff check app tests`
- `backend/.venv/bin/ruff format --check app tests`
- `backend/.venv/bin/pytest -vv`
- `backend/.venv/bin/pytest --cov=app --cov-report=term-missing`
- `backend/.venv/bin/bandit -r app`
- `backend/.venv/bin/pip-audit`
- `npm run lint`
- `npm run typecheck`
- `npm run test`
- `npm run test:e2e`
- `npm run build`
- `npm audit --omit=dev`

## Source Validation

- Backend compile: **PASS**
- Backend Ruff lint/format: **PASS**
- Backend tests: **37 passed, 2 skipped**
- Backend coverage: **71%**
- Bandit: **PASS**, no issues
- pip-audit: **PASS**, no known vulnerabilities for audited PyPI packages
- Frontend lint: **PASS**, 0 errors and 1 existing Fast Refresh warning in `app/layout.tsx`
- Frontend typecheck: **PASS**
- Frontend unit/component tests: **PASS**, 5 files and 19 tests
- Frontend Playwright E2E: **PASS**, 1 Chromium spec
- Frontend build: **PASS**
- npm audit: **PASS**, 0 vulnerabilities

## Remaining Follow-Up

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Several scaffolded enterprise modules remain low coverage, reflected in the 71% backend coverage.
