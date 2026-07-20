# Docker Runtime Guide

Updated on 2026-07-20.

## Services

The Compose stack defines PostgreSQL/pgvector, Redis, MinIO, MinIO init, backend, ingestion/evaluation/report workers, frontend, optional Ollama, and optional observability services: Prometheus, Grafana, and OpenTelemetry collector.

## Commands

```bash
cp .env.example .env
docker compose config
docker compose build
docker compose --profile observability up -d
docker compose --profile observability ps
docker compose logs --no-color
```

Optional Ollama profile:

```bash
docker compose --profile ollama up -d
```

## Health Checks

- PostgreSQL uses `pg_isready`.
- Redis uses `redis-cli ping`.
- MinIO uses its live health endpoint.
- Backend uses `/api/v1/health/live`.
- Frontend uses an HTTP fetch to `/`.
- Ingestion worker uses Celery inspect ping.
- Evaluation worker uses Celery inspect ping against the `evaluation` node.
- Report worker uses Celery inspect ping against the `reports` node.

## Runtime Validation Status

On 2026-07-20, Docker runtime validation passed on this machine with Docker 29.6.2 and Docker Compose v5.3.1. Backend and frontend images built, the observability profile launched, Alembic drift check passed, all core containers were healthy, Prometheus scraped backend and worker targets with `up=1`, and Playwright E2E passed against the Dockerized frontend/backend.

Prometheus scrapes:

- `backend:8000`
- `ingestion-worker:9101`
- `evaluation-worker:9102`
- `report-worker:9103`

Known caveats:

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Grafana dashboards and OpenTelemetry traces were not deeply asserted in this pass.

See `docs/deployment/full-runtime-validation-matrix.md` for the component matrix.
