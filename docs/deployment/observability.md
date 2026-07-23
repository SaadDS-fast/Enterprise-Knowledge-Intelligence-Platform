# Observability

Prometheus scrapes:

- backend `/metrics`;
- ingestion worker metrics;
- evaluation worker metrics;
- report worker metrics.

Grafana dashboard provisioning includes `EKIP Agentic Runtime` with panels for:

- agent runs and durations;
- tool calls, replans, and fallbacks;
- research jobs and exports;
- infrastructure target health.

Prometheus alert rules cover backend/worker unavailability, repeated research failures,
external-provider failures, elevated citation rejections, export failures, and retry backlog.

Metrics, alerts, logs, and traces must not use questions, excerpts, document IDs, job IDs, user IDs,
tenant IDs, URLs, filenames, signed URLs, or tokens as labels or attributes.
