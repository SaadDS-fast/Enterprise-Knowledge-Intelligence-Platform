# Docker Runtime Guide

Updated on 2026-07-20.

## Services

The Compose stack defines:

- `postgres` using `pgvector/pgvector:pg16`
- `redis`
- `minio`
- `minio-init`
- `backend`
- `ingestion-worker`
- `evaluation-worker`
- `report-worker`
- `frontend`
- optional `ollama` profile
- optional observability services: `prometheus`, `grafana`, `otel-collector`

## Commands

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose up -d
docker compose ps
docker compose logs --no-color
```

Optional profiles:

```bash
docker compose --profile observability up -d
docker compose --profile ollama up -d
```

## Health Checks

- PostgreSQL uses `pg_isready`.
- Redis uses `redis-cli ping`.
- MinIO uses its live health endpoint.
- Backend uses `/api/v1/health/live`.
- Frontend uses an HTTP fetch to `/`.
- Ingestion worker uses Celery inspect ping.

## Runtime Validation Status

On the current machine, `docker --version`, `docker compose version`, and `docker info` all failed with `command not found`. Runtime launch and service health validation must be performed on a Docker-capable host.

See `docs/deployment/full-runtime-validation-matrix.md` for the latest runtime validation attempt and component matrix.
