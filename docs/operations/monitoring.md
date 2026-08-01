# Monitoring

Monitor HTTP rates/latency, ingestion outcomes, queue depth, extraction quality, retrieval
states, conflicts, absence, generation verification/fallback, circuit state, Agent and
Research terminal states, PostgreSQL/Redis connections, worker utilization, and container
CPU/memory. Alert on repeated 5xx, stuck processing, queue growth, fallback spikes,
authorization denials, readiness failure, and storage inconsistency.

Labels must be bounded. Passwords, JWTs, keys, query/document text, filenames, object keys,
vectors, embeddings, raw candidates, prompts, and reasoning are forbidden in telemetry.

Use the bounded request/correlation ID to connect browser/API responses, retrieval and
optional generation operations, and audit events. Audit action and outcome labels must be
enumerated and actor/workspace identifiers scoped; never add document/query text, JWTs,
prompts, evidence packets, raw model output, object keys, or reasoning to records or labels.
