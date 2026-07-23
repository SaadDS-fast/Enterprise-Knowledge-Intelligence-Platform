# Resilience Runbook

Use disposable validation data and never record document contents, tokens, or signed URLs.

Redis outage:

1. Start ingestion or research dispatch.
2. Stop Redis.
3. Confirm sanitized failure or retry/dispatch state.
4. Restart Redis.
5. Confirm reconciliation and no duplicate job or artifact.

MinIO outage:

1. Start report generation.
2. Stop MinIO before export.
3. Confirm bounded failure/retry state.
4. Restart MinIO.
5. Confirm one artifact per requested format with stable checksum semantics.

Worker restart:

1. Start ingestion or report generation.
2. Restart the relevant worker.
3. Confirm terminal state remains obtainable and no duplicate completed rows/artifacts appear.

PostgreSQL interruption:

Use only a short controlled interruption. Confirm typed safe errors, recovery, and no corrupt state
transitions.
