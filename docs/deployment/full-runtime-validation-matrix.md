# Full Runtime Validation Matrix

Updated on 2026-07-20 from branch `fix/runtime-reliability-and-e2e`.

## Docker Gate

Runtime validation is unblocked on this machine.

```text
Docker version 29.6.2
Docker Compose version v5.3.1
docker info succeeded
```

## Matrix

| Component | Config validated | Container started | Health passed | Integration passed |
| --- | ---: | ---: | ---: | ---: |
| PostgreSQL/pgvector | Yes | Yes | Yes | Yes, Alembic check and runtime chunk/vector persistence |
| Redis | Yes | Yes | Yes | Yes, Celery broker and outage recovery |
| MinIO | Yes | Yes | Yes | Yes, upload storage and outage rollback |
| Backend | Yes | Yes | Yes | Yes, API runtime probes passed |
| Ingestion worker | Yes | Yes | Yes | Yes, Celery task execution and metrics |
| Evaluation worker | Yes | Yes | Yes | Yes, health and Prometheus scrape |
| Report worker | Yes | Yes | Yes | Yes, health and Prometheus scrape |
| Frontend | Yes | Yes | Yes | Yes, Playwright E2E passed |
| Prometheus | Yes | Yes | Started | Yes, backend and worker targets `up=1` |
| Grafana | Yes | Yes | Started | Basic startup verified; deeper dashboards not validated |
| OpenTelemetry | Yes | Yes | Started | Collector startup verified; trace assertions not validated |

## Commands Completed

```bash
docker compose config
docker compose build
docker compose build backend
docker compose --profile observability up -d
docker compose run --rm backend alembic check
docker compose --profile observability ps
npm run test:e2e
```

Additional live probes validated completed-task retry, Redis outage recovery, MinIO outage rollback, Prometheus `up`, and worker task metrics.

## Remaining Follow-Up

- Ollama profile validation.
- Load/resilience testing.
- Deeper Grafana dashboard and OpenTelemetry trace assertions.
