# Phase 3 PostgreSQL And pgvector Data Path

Implemented on 2026-07-20.

## Changes

- Added incremental Alembic migration `b4a8e9d12f31_pgvector_indexes.py`.
- Added PostgreSQL-only pgvector extension initialization in the migration.
- Added production-oriented PostgreSQL indexes for:
  - document workspace/status/update filtering
  - document-version lookup by document and version number
  - chunk filtering by workspace, document version, and ordinal
  - ingestion job filtering by workspace/status/update time
  - chunk embedding cosine search with an ivfflat pgvector index
- Updated Alembic online migrations to create the `vector` extension before running migrations on PostgreSQL, which allows a fresh PostgreSQL database to apply the already-committed initial migration without editing it.
- Added skipped-by-default PostgreSQL integration tests in `test_postgres_pgvector.py`.

## PostgreSQL Test Coverage Added

The optional tests run only when `POSTGRES_TEST_DATABASE_URL` is set to a disposable PostgreSQL database.

They cover:

- migration from base to head
- pgvector extension presence
- vector index presence
- embedding insert and cosine similarity retrieval
- workspace filtering
- document-version filtering
- rollback behavior
- connection recovery through a post-rollback `SELECT 1`

## Validation

Commands run from `backend/`:

```bash
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -vv
DATABASE_URL=sqlite+aiosqlite:////tmp/ekip_phase3_alembic.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite+aiosqlite:////tmp/ekip_phase3_alembic.db .venv/bin/alembic check
```

Results:

- Ruff lint: passed.
- Ruff format check: passed.
- Pytest: 20 passed, 2 skipped. The skipped tests require `POSTGRES_TEST_DATABASE_URL`.
- Alembic upgrade on a fresh disposable SQLite database: passed.
- Alembic check on that database: passed, no new operations detected.

## Remaining Runtime Gap

PostgreSQL/pgvector runtime validation was not executed because no Docker/PostgreSQL service is available in the current environment. The code now includes the migration and integration tests needed to validate it on a Docker-capable machine.
