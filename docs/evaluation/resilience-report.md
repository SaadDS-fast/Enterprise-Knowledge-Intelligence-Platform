# Resilience Report

The release matrix records Redis, MinIO, worker, PostgreSQL, backend restart, and external-provider
failure outcomes in `VALIDATION_REPORT.md`.

Final 2026-07-23 hardening probe:

- `report-worker` restart completed successfully.
- Worker returned to Docker `healthy` state.
- Backend, frontend, PostgreSQL, Redis, MinIO, ingestion worker, evaluation worker, Prometheus,
  Grafana, and OpenTelemetry collector remained running.

Previously validated Redis and MinIO outage outcomes are retained in `VALIDATION_REPORT.md`.

Safe identifiers may include request IDs, job IDs, task IDs, state transitions, retry counts, final
outcomes, and artifact counts. Do not record credentials, signed URLs, filenames, tenant names, or
document contents.
