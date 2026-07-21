# Known Limitations

Updated on 2026-07-21 from branch `feature/controlled-agentic-rag`.

## Implemented And Runtime-Tested

- Dockerized PostgreSQL/pgvector, Redis, MinIO, backend, frontend, ingestion worker, evaluation worker, report worker, Prometheus, Grafana, and OpenTelemetry collector.
- PostgreSQL Alembic drift check against the Docker database.
- Celery ingestion with idempotent completed-task retry.
- Redis outage handling with automatic retry-pending dispatch recovery.
- MinIO outage handling with sanitized error response and no persisted document row.
- Prometheus scraping of backend and worker metrics endpoints.
- Browser E2E for auth, upload, ingestion, search, evidence display, abstention, tenant isolation, logout, and cleanup.
- Bandit, pip-audit, npm audit, backend tests, frontend tests, typecheck, lint, and production build.
- Controlled agent orchestration foundation with disabled-by-default API, deterministic planner, allowlisted tools, budgets, safe persistence, and audit events.

## Remaining Limitations

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Grafana and OpenTelemetry containers start, but dashboard content, alerting, and trace assertions were not deeply validated.
- Several scaffolded modules remain low coverage, including agent, cache, document lifecycle/retention, SSRF, egress policy, audit persistence, and redaction paths.
- Validation data from throwaway runtime probes remains in the Docker database except for documents explicitly cleaned by the Playwright test.
- Agentic RAG is not enabled by default and has no frontend workflow in this phase.
- External network tools, web search, direct SQL tools, shell tools, and autonomous report generation are intentionally not implemented.

## Notes

- The Redis outage test intentionally produced broker reconnect warnings in worker logs; workers recovered and processed the retry-pending job.
- The MinIO outage test intentionally produced backend storage exception logs; the API response stayed sanitized and no document row persisted.
- Agent persistence stores operational summaries only; private chain-of-thought storage is intentionally excluded.
