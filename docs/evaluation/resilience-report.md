# Resilience Report

The release matrix records Redis, MinIO, worker, PostgreSQL, backend restart, and external-provider
failure outcomes in `VALIDATION_REPORT.md`.

Final 2026-07-23 v0.2.1 operational hardening probe:

- Redis dispatch outage recovered from `dispatch_failed` to completed after Redis restart.
- MinIO export outage recovered with exactly one markdown/PDF/DOCX artifact each and valid
  downloaded DOCX.
- Backend restart completed a research job after service recovery.
- `report-worker` restart completed successfully.
- `ingestion-worker` restart completed successfully with one document version and one chunk.
- PostgreSQL interruption returned a sanitized 500 during outage, then health and Alembic check
  recovered.
- Cancellation persisted `CANCELLED`, repeated cancel remained safe, and cancelling a completed
  job returned 409.
- Idempotent research replay returned the same job and one artifact per requested format.
- Backend, frontend, PostgreSQL, Redis, MinIO, ingestion worker, evaluation worker, Prometheus,
  Grafana, and OpenTelemetry collector remained running.

Safe identifiers may include request IDs, job IDs, task IDs, state transitions, retry counts, final
outcomes, and artifact counts. Do not record credentials, signed URLs, filenames, tenant names, or
document contents.
