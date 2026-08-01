# Operations runbook

1. Confirm `/health/live` and `/health/ready`, Compose health, queue depth, database and
   object-storage availability.
2. Correlate a sanitized request ID through API, worker, retrieval/generation metric, and
   audit event; never log document bodies, tokens, evidence packets, or provider output.
3. For ingestion failures, preserve the last valid version, inspect the safe category,
   then use idempotent reprocess.
4. For provider failures, confirm deterministic fallback and circuit state; do not bypass
   verification or pull a model automatically.
5. For suspected isolation failures, stop affected access and follow incident response.
6. Back up before migrations and verify restore in isolation.
