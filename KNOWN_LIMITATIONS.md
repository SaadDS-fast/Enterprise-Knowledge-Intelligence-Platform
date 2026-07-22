# Known Limitations

Updated on 2026-07-22 from branch `feature/controlled-agentic-rag`.

## Implemented And Runtime-Tested

- Dockerized PostgreSQL/pgvector, Redis, MinIO, backend, frontend, ingestion worker, evaluation worker, report worker, Prometheus, Grafana, and OpenTelemetry collector.
- PostgreSQL Alembic drift check against the Docker database.
- Celery ingestion with idempotent completed-task retry.
- Redis outage handling with automatic retry-pending dispatch recovery.
- MinIO outage handling with sanitized error response and no persisted document row.
- Prometheus scraping of backend and worker metrics endpoints.
- Browser E2E for auth, upload, ingestion, search, evidence display, abstention, tenant isolation, logout, and cleanup.
- Bandit, pip-audit, npm audit, backend tests, frontend tests, typecheck, lint, and production build.
- Controlled internal-document agent with disabled-by-default API, deterministic planner, typed internal tools, retrieval retry, evidence diagnosis, citation-aware synthesis, safety review, budgets, safe persistence, audit events, and fallback to adaptive RAG.
- Optional approved external-source tools for disabled, deterministic, SearXNG, Wikipedia, and arXiv providers, gated by request opt-in and disabled-by-default feature flags.
- SSRF/outbound validation for approved provider calls and prompt-injection scanning for external excerpts.
- Unified multi-source evidence normalization, scoped deduplication, deterministic rank fusion, context-budget management, claim-level verification, conflict detection, citation validation, deterministic grounded synthesis, and evaluation metric aggregation.
- Disabled-by-default asynchronous cited research reports using the existing controlled agent, report worker queue, PostgreSQL/Redis/Celery, MinIO-compatible storage abstraction, scoped idempotency, cancellation, signed artifact downloads, and markdown/PDF/DOCX exports.
- Disabled-by-default frontend workspaces for controlled agent queries, safe run timelines,
  asynchronous research submission, report polling/cancellation, artifact downloads, and gated
  Docker browser validation.

## Remaining Limitations

- Ollama profile validation was not run.
- Load/resilience testing was not run.
- Grafana and OpenTelemetry containers start, but dashboard content, alerting, and trace assertions were not deeply validated.
- Several scaffolded modules remain low coverage, including cache, document lifecycle/retention, SSRF, egress policy, audit persistence, and redaction paths.
- Validation data from throwaway runtime probes remains in the Docker database except for documents explicitly cleaned by the Playwright test.
- Agentic RAG and agentic research are still disabled by default and require explicit backend and
  frontend feature flags.
- External-source tools are not enabled by default and were runtime-validated with the deterministic no-internet provider. Live SearXNG and live public internet validation were not run.
- Optional Ollama claim verification/synthesis interfaces are documented as a future path; this phase uses deterministic verification and synthesis by default.
- Arbitrary browsing, user-supplied URLs, direct SQL tools, shell tools, unrestricted external APIs, admin UI, AWS deployment, and autonomous unrestricted agents are intentionally not implemented.

## Notes

- The Redis outage test intentionally produced broker reconnect warnings in worker logs; workers recovered and processed the retry-pending job.
- The MinIO outage test intentionally produced backend storage exception logs; the API response stayed sanitized and no document row persisted.
- Agent persistence stores operational summaries only; private chain-of-thought storage is intentionally excluded.
