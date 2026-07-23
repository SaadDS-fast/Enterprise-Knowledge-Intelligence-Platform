# Enterprise Knowledge Intelligence Platform (EKIP)

A local-first, multi-tenant document intelligence platform built with FastAPI,
Next.js, PostgreSQL/pgvector, Redis, and optional MinIO/Celery infrastructure.

## What works

- Account registration, JWT login, workspace isolation, and role-aware document actions
- Secure file validation and local/MinIO object storage
- PDF, DOCX, text, Markdown, HTML, CSV, and source-code ingestion
- Background-compatible parsing, normalization, chunking, deterministic embeddings, and indexing
- Hybrid BM25 + semantic retrieval, reranking, evidence sufficiency, and abstention
- Zero-cost extractive answer generation; optional Ollama mode; optional paid provider adapters
- Research briefs, evaluation runs, Prometheus metrics, structured logs, and security middleware
- Next.js interface for authentication, documents, search, research, and evaluation
- Disabled-by-default controlled agent orchestration foundation under `/api/v1/agent`

## Zero-cost guarantee boundary

The repository requires no paid API or cloud account for its default local mode. Docker,
PostgreSQL, pgvector, Redis, MinIO, FastAPI, Next.js, and the extractive provider are open
source. Hardware, electricity, internet, and any cloud deployment remain external costs.
OpenAI/Azure model adapters are optional and never activated by default. The included Terraform configuration targets only the local Docker engine; no billable cloud resources are defined.

## Fastest start with Docker

```bash
cp .env.example .env
docker compose up --build
```

Open the frontend at `http://localhost:3000` and API docs at `http://localhost:8000/docs`.
The default Docker setup uses PostgreSQL, Redis, MinIO, and a Celery ingestion worker.
The backend container runs Alembic migrations before starting the API, and `minio-init`
creates the local object-storage bucket.

Runtime validation requires Docker to be installed and the Docker daemon to be running.
The 2026-07-23 operational hardening validation on branch
`release/v0.2.1-operational-hardening` passed against the real PostgreSQL/Redis/MinIO/Celery
stack, including Redis dispatch recovery, MinIO export outage recovery, backend/report-worker/
ingestion-worker restarts, PostgreSQL interruption recovery, cancellation/idempotency,
Prometheus/Grafana/OpenTelemetry checks, live SearXNG opt-in search, default and enabled
Playwright browser suites, and 5/10/20-user local load probes. Default feature flags were
restored afterward.

The 2026-07-20 validation on branch `fix/runtime-reliability-and-e2e` passed with
Docker 29.6.2 and Docker Compose v5.3.1, including the observability profile,
worker metrics scraping, Redis outage recovery, MinIO outage rollback, and
Playwright browser E2E; see `docs/deployment/full-runtime-validation-matrix.md`.

## Lightweight local start without Docker

```bash
cp .env.example .env
# Change DATABASE_URL to sqlite+aiosqlite:///./ekip.db and keep OBJECT_STORAGE_PROVIDER=local
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e "./backend[dev]"
cd backend && AUTO_INIT_DB=true uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

## Validation

```bash
cd backend
pytest
ruff check app tests
python -m compileall app
cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

## Important production work

Before production, use a managed secret store, TLS, enterprise identity provider, immutable
container tags, backup/restore drills, a real malware scanner, migrations rather than automatic
table creation, persistent rate limiting, and security review of the chosen local or hosted model.

## Retrieval Diagnosis

Search responses include `retrieval_diagnosis`, a safe structured field that distinguishes
directly sufficient evidence, evidence recovered after retry, unresolved retrieval failure,
knowledge absence, partial evidence, conflicting evidence, and ambiguous queries. The retry
path expands retrieval without relaxing tenant, workspace, document, or security filters.

## Controlled Agentic RAG

The controlled agent foundation is intentionally disabled by default:

```env
AGENTIC_RAG_ENABLED=false
AGENT_WEB_SEARCH_ENABLED=false
WEB_SEARCH_PROVIDER=disabled
AGENT_EXTERNAL_APIS_ENABLED=false
EVIDENCE_MAX_ITEMS=12
EVIDENCE_RRF_K=60
EVIDENCE_MIN_SUPPORT_SCORE=0.65
AGENT_RESEARCH_ENABLED=false
AGENT_RESEARCH_ALLOWED_FORMATS=markdown,pdf,docx
```

`POST /api/v1/search` remains the stable non-agentic RAG endpoint. Agentic behavior is isolated
under `POST /api/v1/agent/query`, `GET /api/v1/agent/runs/{run_id}`, and disabled-by-default
research report endpoints under `/api/v1/agent/research`. The agent now executes
typed internal tools for metadata inspection, query reformulation, internal retrieval, evidence
verification, retrieval diagnosis, answer synthesis, and safety review. It reuses the existing
hybrid retriever, reranker, retrieval retry, evidence sufficiency, citations, diagnosis, and
abstention paths. Optional external-source tools are also available behind explicit request and
feature-flag gates for approved providers only: deterministic tests, self-hosted SearXNG,
Wikipedia, and arXiv. Disabled mode makes no network call and remains zero-cost.
The agent normalizes internal and external results into a unified evidence model, performs
deterministic deduplication and reciprocal-rank fusion, verifies claims against cited evidence,
validates citations, detects practical conflicts, and exposes a safe outcome without hidden
reasoning.

The research workflow runs asynchronously through the existing report worker when Celery is
enabled. It creates cited markdown/PDF/DOCX artifacts through the configured object-storage
provider, scopes artifact keys by tenant/workspace/job, supports cancellation and scoped
idempotency, and exposes short-lived signed download parameters. It does not add arbitrary
browsing, unrestricted external APIs, report email delivery, or a major frontend workspace.

See `docs/architecture/controlled-agentic-rag.md` and
`docs/architecture/agentic-frontend-workspace.md`,
`docs/architecture/external-tool-providers.md`,
`docs/architecture/multi-source-evidence.md`,
`docs/api/agent-query-api.md`,
`docs/api/agentic-research-api.md`,
`docs/security/agent-tool-security.md`, and
`docs/security/external-content-threat-model.md`.
