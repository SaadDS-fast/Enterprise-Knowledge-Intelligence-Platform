# Runtime Data Flow

Updated on 2026-07-20.

## Modes

### Synchronous Development Mode

```text
Next.js
-> FastAPI
-> SQLite
-> local filesystem storage
-> FastAPI BackgroundTasks
-> ingestion pipeline
-> deterministic local embeddings
-> in-process hybrid retrieval
-> extractive local answer provider
```

Use this mode for zero-cost development on machines without Docker:

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./ekip.db \
JOB_EXECUTION_MODE=inline \
OBJECT_STORAGE_PROVIDER=local \
AUTO_INIT_DB=true \
.venv/bin/uvicorn app.main:app --reload
```

### Asynchronous Local Stack Mode

```text
Next.js container
-> FastAPI container
-> Alembic migration on startup
-> PostgreSQL with pgvector
-> MinIO object storage
-> Redis broker/result backend
-> Celery ingestion worker
-> scoped source/chunk/vector persistence
-> Prometheus metrics
-> optional Grafana and OpenTelemetry collector profile
```

Use this mode on a Docker-capable machine:

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
```

## Ingestion Lifecycle

```text
Upload
-> authorization
-> MIME and extension validation
-> malware-scan extension point
-> scoped quarantine object key
-> ingestion job submitted
-> Celery task with deterministic task ID
-> parsing
-> normalization
-> chunking
-> embedding
-> source object key
-> chunk/vector persistence
-> document ready
```

Current explicit stages are `pending`, `validating`, `quarantined`, `scanning`, `parsing`, `normalizing`, `chunking`, `embedding`, `indexing`, `completed`, `failed`, and `cancelled`.

## Service Roles

- PostgreSQL/pgvector: durable relational data, vector column storage, and production vector indexes.
- Redis: Celery broker, Celery result backend, and future distributed cache/rate-limit backing store.
- MinIO: local object storage for quarantined uploads and approved source objects.
- Celery: asynchronous ingestion execution in local-stack mode.
- Prometheus: API and retrieval/diagnosis/ingestion metrics.

## Current Validation Boundary

Docker is not installed on the current machine, so PostgreSQL, Redis, MinIO, Celery, Prometheus, Grafana, and OpenTelemetry were syntax/config validated but not runtime-launched here.
