# Full Runtime Validation Matrix

Updated on 2026-07-23 from branch `release/v0.2.1-operational-hardening`.

## v0.2.1 Result

**PASS** for the local Docker operational-hardening profile. The validation covered default,
observability, and web-search Compose configs; Alembic upgrade/drift check; backend/frontend/
worker health; Redis dispatch outage recovery; MinIO export outage recovery; backend,
report-worker, and ingestion-worker restarts; PostgreSQL interruption recovery; cancellation;
idempotency; tenant isolation; Prometheus/Grafana/OpenTelemetry; live SearXNG explicit opt-in
search; default and enabled Playwright suites; and local 5/10/20-user load probes.

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
| Grafana | Yes | Yes | Started | Yes, API returned `EKIP Agentic Runtime` dashboard |
| OpenTelemetry | Yes | Yes | Started | Yes, collector debug exporter logged backend trace batch |
| SearXNG | Yes | Yes | Yes | Yes, live opt-in `/agent/query` returned external evidence and citations |

## Commands Completed

```bash
docker compose config
docker compose build
docker compose build backend
docker compose --profile observability up -d
docker compose --profile web-search config
docker compose run --rm backend alembic check
docker compose --profile observability ps
npm run test:e2e
E2E_AGENTIC_ENABLED=true npm run test:e2e
```

Additional live probes validated completed-task retry, Redis outage recovery, MinIO export outage
recovery, PostgreSQL interruption recovery, Prometheus targets/metrics, Grafana dashboard API,
OpenTelemetry trace export, live SearXNG evidence, and worker task metrics.

## Remaining Follow-Up

- Ollama generation validation.
- Production-scale load and destructive resilience testing beyond local Compose interruptions.
- Alert firing and long-term trace retention.
