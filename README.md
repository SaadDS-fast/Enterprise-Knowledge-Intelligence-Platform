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
npm run typecheck
npm run build
```

## Important production work

Before production, use a managed secret store, TLS, enterprise identity provider, immutable
container tags, backup/restore drills, a real malware scanner, migrations rather than automatic
table creation, persistent rate limiting, and security review of the chosen local or hosted model.
