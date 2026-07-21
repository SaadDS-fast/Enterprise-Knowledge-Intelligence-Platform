# Implementation Report

Updated on 2026-07-21.

## Branch And Commit

- Current branch: `feature/controlled-agentic-rag`
- Started from validated commit: `469e561d763ac03e6c416f9ac816c8b0873f30da`
- Release tag: `v0.1.0-enterprise-mvp`
- Commit status: controlled agentic RAG foundation changes ready for commit.

## Controlled Agentic RAG Foundation

Completed in this phase:

- Added disabled-by-default `POST /api/v1/agent/query`.
- Added `GET /api/v1/agent/runs/{run_id}` with workspace-scoped access.
- Preserved existing `POST /api/v1/search` behavior and route contract.
- Added configuration for agent enablement, step/tool/retry budgets, timeout, and planner provider.
- Replaced the lightweight agent scaffold with typed state, enum, schema, planner, policy, budget, registry, executor, orchestrator, and error modules.
- Added deterministic structured planner output validated by Pydantic.
- Added an allowlisted typed tool registry with enabled internal tools and disabled external placeholders.
- Added policy checks for unknown tools, disabled/network tools, forbidden arguments, direct SQL/URL/shell-like planner data, and workspace scope changes.
- Added additive persistence models and migration for `agent_runs`, `agent_steps`, and `agent_tool_calls`.
- Added audit events for agent run lifecycle.
- Added docs for controlled agent architecture and tool security.
- Added tests for transitions, planner validation, tool rejection, budgets, timeout handling, cancellation, tenant/workspace scope, disabled feature flag, safe persistence, no chain-of-thought storage, and `/search` regression.

## Completed Runtime Reliability Work

- Made completed ingestion retries idempotent: completed jobs return existing results without rewriting chunks, vectors, status, or request ids.
- Preserved existing non-null request ids through ingestion status updates.
- Disposed async database connections around Celery task event loops to avoid asyncpg cross-loop reuse.
- Added retryable dispatch states and safe Celery publishing when Redis/broker dispatch fails.
- Added a backend dispatcher loop that republishes `retry_pending` / `dispatch_failed` ingestion jobs after Redis recovery.
- Added worker Prometheus metrics for task received/completed/failed/retried counts, active tasks, queue delay, and duration.
- Added worker metrics servers and Prometheus scrape targets for ingestion, evaluation, and report workers.
- Added Playwright browser E2E coverage for registration, login, upload, ingestion, search, abstention, tenant isolation, logout, and cleanup.
- Kept Vitest and Playwright suites separate by excluding `tests/e2e/**` from Vitest.

## Docker Runtime Validation

The full observability stack was rebuilt and launched:

```text
docker compose config -> passed
docker compose build -> passed
docker compose build backend -> passed after final backend patch
docker compose --profile observability up -d -> passed
docker compose run --rm backend alembic check -> no new upgrade operations
docker compose --profile observability ps -> services healthy/running
```

Runtime probes passed:

- Completed retry for job `b1f52514-8a77-489b-afc7-40a90f6d9ae3`.
- Redis outage recovery for job `54a2de89-f572-4f83-91f3-c8cc22247702`.
- MinIO outage rollback for workspace `5396ae34-4929-4e10-bd15-254b2fba0d13`.
- Prometheus `up=1` for backend and all three worker scrape targets.

## Validation Results

- Backend tests: 50 passed, 2 skipped.
- Backend coverage: 74%.
- Controlled agent targeted tests: 13 passed.
- Frontend unit/component tests: 19 passed.
- Frontend Playwright E2E: 1 passed.
- Frontend build/typecheck/lint: passed.
- Bandit, pip-audit, and npm audit: passed.
- Migration smoke: disposable SQLite Alembic `upgrade head` passed through `c8f4a2d91b77`.
- Docker smoke: `docker compose config` passed; running observability stack remained healthy.

## Follow-Up

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Coverage remains uneven in scaffolded agent/cache/security modules.
- Agentic mode remains disabled by default and should not be enabled globally until future phases add deeper operator review, dashboards, and production rollout controls.
- Web search, external APIs, autonomous research reports, and major frontend agent UX are intentionally not included in this phase.
