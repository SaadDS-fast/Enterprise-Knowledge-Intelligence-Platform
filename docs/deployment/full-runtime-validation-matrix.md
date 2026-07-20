# Full Runtime Validation Matrix

Updated on 2026-07-20 from branch `validation/full-runtime-stack`.

## Docker Gate

Runtime validation is blocked on this machine because Docker is not installed on `PATH`.

Commands run:

```bash
docker --version
docker compose version
docker info
```

All three returned:

```text
zsh:1: command not found: docker
```

No containers were built or started. No Docker volumes were created. No `.env` file was created because validation did not proceed past the Docker capability gate.

## Matrix

| Component | Config validated | Container started | Health passed | Integration passed |
| --- | ---: | ---: | ---: | ---: |
| PostgreSQL/pgvector | Yes, prior YAML parse only | No | No | No |
| Redis | Yes, prior YAML parse only | No | No | No |
| MinIO | Yes, prior YAML parse only | No | No | No |
| Backend | Yes, prior YAML parse only | No | No | No |
| Ingestion worker | Yes, prior YAML parse only | No | No | No |
| Evaluation worker | Yes, prior YAML parse only | No | No | No |
| Report worker | Yes, prior YAML parse only | No | No | No |
| Frontend | Yes, prior YAML parse only | No | No | No |
| Prometheus | Yes, prior YAML parse only | No | No | No |
| Grafana | Yes, prior YAML parse only | No | No | No |
| OpenTelemetry | Yes, prior YAML parse only | No | No | No |

## Baseline Checks Completed Before Docker Gate

Backend:

- `python -m compileall app tests`: passed.
- `ruff check app tests`: passed.
- `ruff format --check app tests`: passed.
- `pytest -vv`: 35 passed, 2 skipped.
- `pytest --cov=app --cov-report=term-missing`: 72% coverage.
- `bandit -r app`: passed, no issues.
- `pip-audit --cache-dir /tmp/ekip-pip-audit-cache`: no known vulnerabilities for auditable packages.

Frontend:

- `rm -rf node_modules .next`: completed.
- `npm ci`: passed.
- `npm run lint`: passed with 0 errors and 1 known Next.js metadata warning.
- `npm run typecheck`: passed.
- `npm run test`: 5 files, 19 tests passed.
- `npm run build`: passed.
- `npm audit --omit=dev`: 0 vulnerabilities.

## Required Follow-Up On Docker-Capable Host

Run:

```bash
cp .env.example .env
docker compose config
docker compose build --no-cache
docker compose up -d postgres redis minio minio-init
docker compose ps
docker compose logs --no-color postgres redis minio minio-init
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic check
docker compose up -d backend ingestion-worker evaluation-worker report-worker
docker compose up -d frontend prometheus grafana otel-collector
```

Only after those services are actually healthy should runtime ingestion, pgvector similarity, MinIO object lifecycle, Celery processing, retrieval diagnosis, tenant isolation, and observability be marked as integration-passed.
