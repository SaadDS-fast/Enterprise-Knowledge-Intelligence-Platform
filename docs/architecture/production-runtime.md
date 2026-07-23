# Production Runtime

This repository is local-first and has not been deployed to AWS. The production-oriented local
profile is Docker Compose with PostgreSQL/pgvector, Redis, MinIO, FastAPI, Next.js, Celery
workers, Prometheus, Grafana, and OpenTelemetry collector.

Authoritative runtime controls:

- backend feature flags for agent, research, and external providers;
- frontend feature flags only for visibility;
- request rate limits;
- body and upload size limits;
- upload extension and MIME allowlists;
- agent step, tool-call, retry, timeout, evidence, and provider-response budgets;
- research source, report-size, concurrency, queue-depth, timeout, cancellation, and export limits;
- signed artifact URL expiry;
- low-cardinality metrics and alerts.

Default operation keeps agentic RAG, research, and external providers disabled.
