# Phase 4 Asynchronous Worker System

Implemented on 2026-07-20.

## Changes Completed

- Added explicit ingestion stage constants for the ingestion lifecycle.
- Preserved the default inline local-development fallback.
- Strengthened the Celery production path:
  - deterministic task ID set to the ingestion job ID
  - task queue set to `ingestion`
  - request ID propagated through Celery headers and task kwargs
  - retry backoff and retry jitter enabled
  - retry limit retained at 3 attempts
  - soft and hard task time limits added
- Propagated API request IDs from document upload into ingestion dispatch.
- Stored request ID and structured error type metadata in ingestion job `result_json`.
- Added unit tests for Celery dispatch and inline background-task dispatch.

## Current Upload Flow

```text
Upload request
-> backend authorization
-> file validation and scan hook
-> quarantine object write
-> ingestion job created
-> dispatch by configured mode
   -> inline BackgroundTasks in default local mode
   -> Redis/Celery task in production/Docker mode
-> API returns HTTP 202
-> ingestion pipeline parses, normalizes, chunks, embeds, indexes, approves object
-> document becomes searchable
```

## Validation

Commands run from `backend/`:

```bash
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -vv
```

Results:

- Ruff lint: passed.
- Ruff format check: passed.
- Pytest: 22 passed, 2 skipped.

## Remaining Worker Gaps

- Redis/Celery runtime validation was not executed because the Docker/Redis worker stack is not running in this environment.
- Evaluation and report workers remain separate scaffolded packages and are not yet integrated into the main job orchestration path.
- Job cancellation, dead-letter queues, queue-depth metrics, worker health endpoints, and graceful shutdown tests are still pending.
- The lifecycle state vocabulary is now explicit in code, but the database still stores string values for compatibility with the existing schema and API.
