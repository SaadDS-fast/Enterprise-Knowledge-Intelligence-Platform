# Known Limitations

## Implemented And Tested

- Registration, login, current-user lookup, invalid-login rejection.
- Authenticated document upload and local inline ingestion.
- TXT, Markdown, HTML, CSV, source-code, PDF, and DOCX loaders through upload/search flow.
- BM25, vector similarity, hybrid fusion, reranking, grounded evidence, and abstention.
- Tenant/workspace isolation for document list/detail and search.
- Research and evaluation endpoints.
- Prometheus metrics endpoint.

## Implemented But Not Runtime-Tested

- Dockerized PostgreSQL/pgvector, Redis, MinIO, frontend, backend, and worker stack.
- Celery ingestion-worker path; local validation used inline/background FastAPI tasks.
- Prometheus, Grafana, and OpenTelemetry containers.
- MinIO object storage path; local validation used filesystem storage.
- PostgreSQL/pgvector runtime; validation used SQLite plus migration checks.

## Partially Implemented

- Frontend linting: command exists but is a no-op because no linter is configured.
- Frontend browser workflow: build/typecheck passed, but no browser automation was run.
- Observability: request IDs and metrics work locally; distributed tracing was not enabled in runtime validation.
- Security scanning: Bandit, pip-audit, and npm audit passed; deeper DAST/browser security testing was not run.

## Placeholder Or Low-Coverage Areas

- Agent modules under `backend/app/agents`.
- Cache policy/client paths.
- Document lifecycle/retention/versioning helper modules.
- SSRF, egress policy, audit-event persistence, and redaction modules are present but not broadly runtime-tested.
- Standalone worker packages under `workers/*` were inspected but not executed.

## Planned For Next Stage

- Real frontend lint configuration.
- Browser automation for registration, login, upload, search, evidence display, abstention, and logout.
- Docker runtime validation on a machine with Docker available.
- Runtime validation with PostgreSQL/pgvector, Redis, MinIO, Celery workers, Prometheus, Grafana, and OpenTelemetry.
- Broader coverage for scaffolded enterprise/security/agent modules.
