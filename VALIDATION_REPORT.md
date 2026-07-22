# Validation Report

Validated on 2026-07-22 on branch `feature/controlled-agentic-rag`.

## Environment

- Base agent foundation commit: `14be684`
- Release tag: `v0.1.0-enterprise-mvp`
- Working tree: multi-source evidence aggregation changes ready for commit
- Python: 3.12.13
- Node: v20.20.2
- npm: 10.8.2
- Docker: 29.6.2
- Docker Compose: v5.3.1

## Overall Status

**PASS**

The Dockerized runtime stack passed validation for backend, frontend, PostgreSQL/pgvector, Redis/Celery, MinIO, Prometheus worker scraping, and browser E2E. Ollama profile and load testing remain out of scope for this pass and are documented as follow-up items, not blockers for the requested runtime reliability fixes.

Controlled agentic RAG update: this phase adds unified multi-source evidence aggregation, claim-level verification, conflict detection, citation validation, deterministic grounded synthesis, evaluation metrics, and a disabled-by-default asynchronous cited research-report workflow while keeping agentic mode and external access disabled by default. `/search` remains unchanged, internal agent behavior remains working, and external access requires both a feature flag and `allow_external_sources=true`.

## Key Runtime Results

- Completed-task retry: **PASS**. A duplicate Celery task for completed job `b1f52514-8a77-489b-afc7-40a90f6d9ae3` returned successfully, preserved request id `a99f349a-631a-4089-9a44-62093233da46`, and kept counts at 1 chunk / 1 embedded chunk. Targeted logs had no asyncpg or event-loop warnings.
- Redis outage recovery: **PASS**. Upload while Redis was stopped returned 202 with job `54a2de89-f572-4f83-91f3-c8cc22247702` marked `retry_pending`; after Redis restart the backend dispatcher automatically published it and the job completed. Database check showed 0 jobs stuck in `retry_pending` or `dispatch_failed`.
- MinIO outage safety: **PASS**. Upload while MinIO was stopped returned sanitized 500 and document count stayed 0 for that workspace.
- Worker metrics: **PASS**. Prometheus targets for `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103`, and `backend:8000` all reported `up=1`. `ekip_worker_tasks_completed_total{worker_role="ingestion"}` reached 4 after runtime probes.
- Browser E2E: **PASS**. Playwright Chromium ran against Dockerized frontend/backend: 1 spec passed covering register, login, upload, ingestion, search evidence, abstention, tenant isolation, logout, and cleanup.
- Internal agent Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true` for the probe only, uploaded document job `4982e894-bc00-4c54-b069-f79f44f7f71f` completed through Celery/PostgreSQL/Redis/MinIO and `/agent/query` run `20bc2a99-e839-468d-87b6-4d970909f327` returned `SUFFICIENT_EVIDENCE`, 1 evidence item, 1 citation, and `abstained=false`. The stack was restored to the default disabled agent posture afterward.
- Agent metrics: **PASS**. `/metrics` exposed `ekip_agent_runs_started_total`, `ekip_agent_runs_completed_total`, `ekip_agent_runs_failed_total`, `ekip_agent_tool_calls_total`, `ekip_agent_replans_total`, `ekip_agent_fallbacks_total`, `ekip_agent_duration_seconds`, and `ekip_agent_tool_duration_seconds`.
- External-disabled runtime: **PASS**. With agent enabled and external providers disabled, internal run `4b52e7e2-2dd2-46cc-bd89-e0a5c5f16310` answered from internal evidence, and public-disabled run `1db97c59-c459-4765-93ba-a8b03c4cf0ab` abstained with no external access.
- Deterministic external runtime: **PASS**. With `WEB_SEARCH_PROVIDER=deterministic`, public run `e4271e7e-b199-458e-a217-f4064478cdf6` returned external provenance and citation; internal-preference run `01a2870f-5ab1-4086-828c-d710c6a84f3c` did not call external search when internal evidence was sufficient.
- External metrics: **PASS**. `/metrics` exposed `ekip_agent_external_tool_calls_total`, `ekip_agent_external_tool_failures_total`, `ekip_agent_external_tool_duration_seconds`, `ekip_agent_external_sources_used_total`, `ekip_agent_ssrf_blocks_total`, and `ekip_agent_external_timeouts_total`.
- Multi-source evidence metrics: **PASS**. `/metrics` exposes evidence, deduplication, claim, conflict, citation, synthesis-fallback, and context-budget metric families with low-cardinality labels only.
- Multi-source Docker runtime probes: **PASS**. Deterministic no-internet runtime covered internal supported run `30a13d77-efaf-4cd8-99ec-da772fc5fc2b`, public external run `854fac77-0904-4aaf-b156-abd43c8142df`, internal-preferred mixed run `9d7a5e72-f089-4d6b-9ace-54c6f7a0865c`, partial run `c71c9c10-f24e-4b8b-9138-2f43c1820cc0`, internal conflict run `08704576-8908-4635-9095-52f57e3bf4cd`, internal/external conflict run `ef36a0f9-be84-43f0-923a-1ee2b430200b`, knowledge-absence run `e9896f8c-a078-42f4-94f1-b29a6935493b`, ambiguous run `0c6580ce-c538-4140-b1b6-bbf0266ba6b7`, prompt-injection run `1c591745-b41d-448f-8d8b-e3a50064a8ea`, and tenant-isolation run `30a54d73-9b9d-4914-8179-eed436c7a155`. Backend was restored to default disabled-agent/external settings afterward.
- Research report tests: **PASS**. Targeted backend research tests passed: 12 tests covering feature flag denial, lifecycle, exports, signed download tampering, idempotency, knowledge absence, conflicts, cancellation, tenant isolation, workspace document-scope denial, and `/search` regression.
- Research report Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true` and `AGENT_RESEARCH_ENABLED=true` for the probe only, Docker API upload job `1985fb7d-2fd7-488b-994a-fa9bf5b0a9b6` completed through PostgreSQL/Redis/MinIO/Celery, research job `b4653536-ffd1-4132-b513-4bd19680e5dd` completed through `report-worker`, agent run `3593b650-7676-4616-b4fe-9a5d6ad33e5c` returned 1 source and 1 verified citation, and markdown/PDF/DOCX downloads passed. Backend and workers were restored to default disabled agent/research flags afterward.

## Commands Run

- `docker compose config`
- `docker compose --profile web-search config`
- `docker compose build`
- `docker compose build backend`
- `docker compose build frontend`
- `docker compose --profile observability up -d`
- `AGENTIC_RAG_ENABLED=true docker compose --profile observability up -d backend ingestion-worker evaluation-worker report-worker`
- `docker compose run --rm backend alembic check`
- `docker compose --profile observability ps`
- Live Docker agent API probe for upload, Celery ingestion, `/agent/query`, citations, evidence, and metrics
- Live Docker deterministic external provider probes for disabled mode, external-enabled mode, and internal-preference mode
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
- Research targeted tests for async lifecycle, exports, idempotency, cancellation, scoped denial, conflict/absence report cases, signed downloads, and `/search` regression

## Source Validation

- Backend compile: **PASS**
- Backend Ruff lint/format: **PASS**
- Backend tests: **113 passed, 2 skipped**
- Backend coverage: **77%**
- Bandit: **PASS**, no issues
- pip-audit: **PASS**, no known vulnerabilities for audited PyPI packages
- Frontend lint: **PASS**, 0 errors and 1 existing Fast Refresh warning in `app/layout.tsx`
- Frontend typecheck: **PASS**
- Frontend unit/component tests: **PASS**, 5 files and 19 tests
- Frontend Playwright E2E: **PASS**, 1 Chromium spec
- Frontend build: **PASS**
- npm audit: **PASS**, 0 vulnerabilities
- Frontend dependency security: **PASS**, `sharp@0.35.3` override resolves the transitive libvips advisory without downgrading Next
- Controlled agent, external provider, and multi-source evidence targeted tests: **PASS**, 65 passed
- Evidence normalization: **PASS**, internal, SearXNG, Wikipedia, arXiv, and approved API paths tested
- Deduplication: **PASS**, external URL duplicates merge and cross-tenant internal evidence never merges
- Rank fusion: **PASS**, deterministic RRF preserves internal priority for organization-specific questions
- Claim verification: **PASS**, supported, partially supported, unsupported, and conflicted statuses tested
- Conflict detection: **PASS**, numeric, date, and owner/entity contradictions tested
- Citation validation: **PASS**, unknown and unrelated citation labels rejected
- Deterministic synthesis: **PASS**, grounded extractive answer and unsupported-claim removal tested
- Evaluation metrics: **PASS**, fixture execution measured support rate 0.5, citation precision 1.0, citation recall 0.75, unsupported claim rate 0.3333, abstention accuracy 1.0, conflict detection accuracy 1.0, and average evidence count 2.5
- SearXNG adapter: **PASS**, parser tests and optional Compose profile config passed; live SearXNG launch was not required for this zero-internet validation pass
- Wikipedia adapter: **PASS**, mocked response parsing passed
- arXiv adapter: **PASS**, mocked Atom parsing passed with hardened XML parser
- SSRF tests: **PASS**, blocked private IPv4/IPv6, localhost, metadata host, Docker hostname, unsafe schemes, and redirects to private destinations
- External prompt injection: **PASS**, malicious external excerpt forced abstention and cleared citations
- External provenance: **PASS**, external citations retain provider/title/canonical URL/retrieval date/excerpt and remain separate from internal citations
- Existing `/search` regression: **PASS**, `/api/v1/search` still returns answer and retrieval diagnosis payload
- Research report targeted tests: **PASS**, 12 passed
- Research exports: **PASS**, markdown, PDF, and DOCX artifacts are generated through the storage abstraction
- Research citation validation: **PASS**, verified citation counts and citation metadata are persisted in the structured report response
- Migration smoke: **PASS**, disposable SQLite Alembic `upgrade head` reached `d9a1f2c3b4e5` and Docker PostgreSQL `alembic check` reported no new upgrade operations
- Docker smoke: **PASS**, `docker compose config` passed and the existing observability stack remained healthy

## Remaining Follow-Up

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Several scaffolded enterprise modules remain low coverage, reflected in the 78% backend coverage.
- Agentic mode, research mode, and external access are disabled by default. Live SearXNG launch, live public internet tests, arbitrary browsing, unrestricted external APIs, major frontend agent UX, admin UI, and AWS deployment are future work.
