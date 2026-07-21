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
```

`POST /api/v1/search` remains the stable non-agentic RAG endpoint. Agentic behavior is isolated
under `POST /api/v1/agent/query` and `GET /api/v1/agent/runs/{run_id}`. The foundation uses a
deterministic structured planner, an allowlisted tool registry, explicit state transitions,
tenant/workspace scope checks, budgets, timeouts, audit events, and persistence tables for safe
operational summaries only. It does not add web search, external APIs, or autonomous report
generation in this phase.

See `docs/architecture/controlled-agentic-rag.md` and
`docs/security/agent-tool-security.md`.
