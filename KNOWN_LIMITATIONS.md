# Known Limitations

Updated on 2026-07-23 from branch `release/v0.2.1-operational-hardening`.

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
- v0.2.1 operational validation for Redis dispatch outage recovery, MinIO export outage recovery,
  backend/report-worker/ingestion-worker restarts, PostgreSQL interruption recovery, cancellation,
  idempotency replay, tenant-isolation denial matrix, Prometheus/Grafana/OpenTelemetry APIs, and
  live SearXNG explicit opt-in search through `/agent/query`.

## Remaining Limitations

- Ollama model generation was not run; local models were listed only.
- Existing documents ingested before the deterministic structure-aware chunking update do not
  automatically receive the new heading/value boundaries or section metadata. Re-upload or
  reprocess those documents before comparing old and new retrieval behavior.
- Load testing was limited to local 5/10/20-user probes and should not be extrapolated to enterprise traffic.
- Deep destructive outage testing was limited to local Compose service interruption/restart probes;
  host crashes, disk exhaustion, network partitions, and multi-node failover were not tested.
- Grafana dashboard provisioning, Prometheus targets, and OpenTelemetry collector trace export were
  API/log validated; alert firing and long-term trace retention were not tested.
- Several scaffolded modules remain low coverage, including cache, document lifecycle/retention, SSRF, egress policy, audit persistence, and redaction paths.
- Validation data from throwaway runtime probes remains in the Docker database except for documents explicitly cleaned by the Playwright test.
- Agentic RAG and agentic research are still disabled by default and require explicit backend and
  frontend feature flags.
- External-source tools are not enabled by default. Deterministic and live SearXNG opt-in paths were
  runtime-validated locally, but live public internet engine quality remains environment-dependent.
- Optional Ollama claim verification/synthesis interfaces are documented as a future path; this phase uses deterministic verification and synthesis by default.
- Arbitrary browsing, user-supplied URLs, direct SQL tools, shell tools, unrestricted external APIs, admin UI, AWS deployment, and autonomous unrestricted agents are intentionally not implemented.

## Notes

- The Redis outage test intentionally produced broker reconnect warnings in worker logs; workers recovered and processed the retry-pending job.
- The MinIO outage test intentionally produced backend storage exception logs; the API response stayed sanitized and no document row persisted.
- Agent persistence stores operational summaries only; private chain-of-thought storage is intentionally excluded.
