# Validation Report

Validated on 2026-07-22 on branch `feature/controlled-agentic-rag`.

## Environment

- Base agent foundation commit: `14be684`
- Release tag: `v0.1.0-enterprise-mvp`
- Working tree: controlled internal RAG agent changes ready for final validation and commit
- Python: 3.12.13
- Node: v20.20.2
- npm: 10.8.2
- Docker: 29.6.2
- Docker Compose: v5.3.1

## Overall Status

**PASS**

The Dockerized runtime stack passed validation for backend, frontend, PostgreSQL/pgvector, Redis/Celery, MinIO, Prometheus worker scraping, and browser E2E. Ollama profile and load testing remain out of scope for this pass and are documented as follow-up items, not blockers for the requested runtime reliability fixes.

Controlled agentic RAG update: this phase integrates a working internal-document agent. Agentic mode remains disabled by default, `/search` remains unchanged, and `/agent/query` is isolated behind `AGENTIC_RAG_ENABLED`.

## Key Runtime Results

- Completed-task retry: **PASS**. A duplicate Celery task for completed job `b1f52514-8a77-489b-afc7-40a90f6d9ae3` returned successfully, preserved request id `a99f349a-631a-4089-9a44-62093233da46`, and kept counts at 1 chunk / 1 embedded chunk. Targeted logs had no asyncpg or event-loop warnings.
- Redis outage recovery: **PASS**. Upload while Redis was stopped returned 202 with job `54a2de89-f572-4f83-91f3-c8cc22247702` marked `retry_pending`; after Redis restart the backend dispatcher automatically published it and the job completed. Database check showed 0 jobs stuck in `retry_pending` or `dispatch_failed`.
- MinIO outage safety: **PASS**. Upload while MinIO was stopped returned sanitized 500 and document count stayed 0 for that workspace.
- Worker metrics: **PASS**. Prometheus targets for `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103`, and `backend:8000` all reported `up=1`. `ekip_worker_tasks_completed_total{worker_role="ingestion"}` reached 4 after runtime probes.
- Browser E2E: **PASS**. Playwright Chromium ran against Dockerized frontend/backend: 1 spec passed covering register, login, upload, ingestion, search evidence, abstention, tenant isolation, logout, and cleanup.
- Internal agent Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true` for the probe only, uploaded document job `4982e894-bc00-4c54-b069-f79f44f7f71f` completed through Celery/PostgreSQL/Redis/MinIO and `/agent/query` run `20bc2a99-e839-468d-87b6-4d970909f327` returned `SUFFICIENT_EVIDENCE`, 1 evidence item, 1 citation, and `abstained=false`. The stack was restored to the default disabled agent posture afterward.
- Agent metrics: **PASS**. `/metrics` exposed `ekip_agent_runs_started_total`, `ekip_agent_runs_completed_total`, `ekip_agent_runs_failed_total`, `ekip_agent_tool_calls_total`, `ekip_agent_replans_total`, `ekip_agent_fallbacks_total`, `ekip_agent_duration_seconds`, and `ekip_agent_tool_duration_seconds`.

## Commands Run

- `docker compose config`
- `docker compose build`
- `docker compose build backend`
- `docker compose build frontend`
- `docker compose --profile observability up -d`
- `AGENTIC_RAG_ENABLED=true docker compose --profile observability up -d backend ingestion-worker evaluation-worker report-worker`
- `docker compose run --rm backend alembic check`
- `docker compose --profile observability ps`
- Live Docker agent API probe for upload, Celery ingestion, `/agent/query`, citations, evidence, and metrics
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
- Agent targeted tests for state transitions, planner validation, typed tools, query reformulation, retrieval retry, evidence diagnosis, safety review, fallback, scoped denial, prompt injection handling, and `/search` regression

## Source Validation

- Backend compile: **PASS**
- Backend Ruff lint/format: **PASS**
- Backend tests: **60 passed, 2 skipped**
- Backend coverage: **74%**
- Bandit: **PASS**, no issues
- pip-audit: **PASS**, no known vulnerabilities for audited PyPI packages
- Frontend lint: **PASS**, 0 errors and 1 existing Fast Refresh warning in `app/layout.tsx`
- Frontend typecheck: **PASS**
- Frontend unit/component tests: **PASS**, 5 files and 19 tests
- Frontend Playwright E2E: **PASS**, 1 Chromium spec
- Frontend build: **PASS**
- npm audit: **PASS**, 0 vulnerabilities
- Frontend dependency security: **PASS**, `sharp@0.35.3` override resolves the transitive libvips advisory without downgrading Next
- Controlled agent targeted tests: **PASS**, 23 passed
- Existing `/search` regression: **PASS**, `/api/v1/search` still returns answer and retrieval diagnosis payload
- Migration smoke: **PASS**, disposable SQLite Alembic `upgrade head` reached `c8f4a2d91b77`
- Docker smoke: **PASS**, `docker compose config` passed and the existing observability stack remained healthy

## Remaining Follow-Up

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Several scaffolded enterprise modules remain low coverage, reflected in the 74% backend coverage.
- Agentic mode is disabled by default; web search, external APIs, autonomous research reports, report exports, and major frontend agent UX are future work.
