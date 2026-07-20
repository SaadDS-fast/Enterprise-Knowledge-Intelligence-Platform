# Validation Report

Validated on 2026-07-18 on Darwin 25.5.0 arm64.

## Environment

- Branch: `validation/current-mvp`
- Commit at validation start: `33a9eb4`
- Python: `backend/.venv/bin/python --version` -> Python 3.12.13
- Node: `node --version` -> v20.20.2
- npm: `npm --version` -> 10.8.2
- Docker: `docker --version` -> command not found

## Overall Status

**PARTIAL PASS**

The local MVP backend and frontend passed source-level, test-suite, and real HTTP validation. The status is not full PASS because Docker runtime validation could not be executed on this machine and several local service integrations were not launched.

Update on 2026-07-20: frontend linting is no longer a no-op. Phase 2 added real ESLint configuration and frontend component tests. Phase 3 added PostgreSQL/pgvector migration/index support with optional integration tests. Phase 4 strengthened ingestion worker dispatch. Overall status remains **PARTIAL PASS** because Docker, PostgreSQL, Redis/Celery, MinIO, browser E2E, Ollama, and load-test runtime validation were not executed.

Runtime RAG intelligence update on 2026-07-20: Docker CLI remains unavailable (`docker: command not found`). The Compose YAML was structurally parsed with 13 services. Retrieval diagnosis, safe API metadata, frontend display, scoped object keys, ingestion/retrieval metrics, and deterministic diagnosis evaluation helpers were implemented and tested. Overall status remains **PARTIAL PASS** because local services were not launched.

## Commands Run

- `npm ci`
- `npm run lint`
- `npm run type-check`
- `npm run build`
- `npm audit --omit=dev`
- `backend/.venv/bin/python -m compileall app tests`
- `backend/.venv/bin/ruff check app tests`
- `backend/.venv/bin/ruff format --check app tests`
- `backend/.venv/bin/pytest -vv`
- `backend/.venv/bin/pytest --cov=app --cov-report=term-missing`
- Programmatic import of all backend modules
- Programmatic FastAPI OpenAPI generation
- `alembic upgrade head`
- `alembic check`
- Real HTTP validation against `uvicorn app.main:app --host 127.0.0.1 --port 8765`
- `bandit -r app`
- `pip-audit --cache-dir /tmp/pip-audit-cache`
- YAML parsing for Docker Compose, Prometheus, Grafana datasource, and OpenTelemetry collector config

## Results

- Backend tests: **20 passed, 0 failed, 0 skipped, 0 errored**
- Phase 4 backend tests: **22 passed, 2 skipped**; skipped tests require `POSTGRES_TEST_DATABASE_URL`
- Runtime RAG backend tests: **35 passed, 2 skipped**; skipped tests require `POSTGRES_TEST_DATABASE_URL`
- Runtime RAG backend coverage: **72%**
- Backend coverage: **70%**
- Python compile: **PASS**
- Ruff lint/format: **PASS**
- Module import check: **PASS**, 159 modules imported, 0 failures
- OpenAPI generation: **PASS**, 14 paths
- Alembic: **PASS**, fresh `upgrade head` and `check`
- Frontend `npm ci`: **PASS** from a clean `node_modules` state
- Frontend lint: **PASS**, real ESLint flat config; 0 errors and 1 warning for the standard Next.js `metadata` export
- Frontend component tests: **PASS**, 5 files and 12 tests
- Runtime RAG frontend component tests: **PASS**, 5 files and 19 tests
- Frontend type-check: **PASS**
- Frontend production build: **PASS**
- npm audit: **PASS**, 0 vulnerabilities
- Bandit: **PASS**, no issues
- pip-audit: **PASS**, no known vulnerabilities for audited packages; local editable package not on PyPI
- Docker Compose syntax: **PARTIAL**, YAML parsed; Docker CLI unavailable for `docker compose config`
- Docker runtime: **NOT RUN**, Docker command not found

## Runtime API And E2E

The real FastAPI app was started with a disposable SQLite DB and local object storage. A scripted HTTP flow passed **36/36** checks:

- Health, registration, login, invalid login, and current-user request
- Authenticated upload and ingestion to completed/indexed status
- TXT, Markdown, HTML, CSV, source-code, PDF, and DOCX upload/ingestion/search
- Empty file, malformed PDF, unsupported extension, MIME mismatch, and path traversal filename checks
- Grounded answers for Project Atlas launch date, owner, and budget with evidence
- Abstention for unrelated fictional-country question
- Document ID filtering
- Tenant document-list, document-detail, and search isolation
- Research create/list
- Evaluation create/list
- Metrics endpoint
- Direct BM25, vector similarity, hybrid fusion, and reranker checks

## Observability

- Request ID middleware produced request IDs in logs and responses.
- `/metrics` returned Prometheus metrics.
- Prometheus, Grafana datasource, and OpenTelemetry collector YAML parsed successfully.
- OpenTelemetry is disabled by default in local validation (`OTEL_ENABLED=false`).
- Grafana/Prometheus/OTel services were not runtime-launched because Docker is unavailable.

## Fixes Made

- Made frontend dependency installation reproducible by normalizing lockfile resolved URLs to the public npm registry and verifying `npm ci`.
- Added `lint` and `type-check` scripts expected by validation; lint currently records that no linter is configured.
- Ignored generated `*.tsbuildinfo`.
- Hardened `DEBUG=release` parsing so host shell environment does not crash settings initialization.
- Enforced extension-specific MIME matching for uploads.
- Tightened evidence sufficiency so stopword overlap does not defeat abstention.
- Added regression tests for DEBUG parsing, TXT/PDF MIME mismatch rejection, and unrelated-question abstention.
- Upgraded backend dependency constraints for vulnerable `pypdf` and dev `pytest`; installed verified versions in the local env.
- Added an initial Alembic schema migration and verified `alembic upgrade head` / `alembic check`.
- Removed a Bandit false positive in an evaluation helper without suppressing the scanner.

## Remaining Limitations

- Docker runtime validation was not executed because Docker is not installed on PATH.
- Docker Compose YAML structure was parsed successfully, but `docker compose config` could not run because Docker is not installed on PATH.
- Frontend lint now uses real ESLint configuration, but browser automation against the Next.js UI was not executed.
- Browser automation against the Next.js UI was not executed; frontend validation was build/typecheck plus backend HTTP API flows.
- Celery worker path, MinIO storage, Redis, PostgreSQL/pgvector, Prometheus, Grafana, and OpenTelemetry were inspected/config-parsed but not launched.
- Several agent/cache/policy modules remain scaffold-like or unexercised by tests, reflected in 70% backend coverage.

## Zero-Cost Confirmation

Default local validation used FastAPI, SQLite, local object storage, deterministic local embeddings, and extractive local answers. No paid API keys or paid cloud services were required.
