from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

POSTGRES_TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="Set POSTGRES_TEST_DATABASE_URL to run PostgreSQL/pgvector integration tests.",
)


def _sync_url(url: str) -> str:
    return url.replace("+asyncpg", "")


@pytest.fixture(scope="module")
def migrated_postgres_url() -> str:
    assert POSTGRES_TEST_DATABASE_URL
    backend_dir = Path(__file__).resolve().parents[2]
    env = os.environ | {
        "DATABASE_URL": POSTGRES_TEST_DATABASE_URL,
        "APP_ENV": "testing",
        "SECRET_KEY": "postgres-test-secret-change-me-123456789",
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return POSTGRES_TEST_DATABASE_URL


@pytest.mark.asyncio
async def test_pgvector_schema_indexes_and_similarity(migrated_postgres_url: str):
    engine = create_async_engine(migrated_postgres_url)
    org_id = uuid4()
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    chunk_id = uuid4()
    other_chunk_id = uuid4()
    vector = [0.0] * 384
    vector[0] = 1.0
    other_vector = [0.0] * 384
    other_vector[1] = 1.0

    async with engine.begin() as connection:
        extension = await connection.scalar(
            text("SELECT extname FROM pg_extension WHERE extname='vector'")
        )
        assert extension == "vector"
        indexes = set(
            (
                await connection.execute(
                    text(
                        """
                        SELECT indexname
                        FROM pg_indexes
                        WHERE schemaname = current_schema()
                        """
                    )
                )
            ).scalars()
        )
        assert "ix_chunks_embedding_cosine_ivfflat" in indexes
        assert "ix_chunks_workspace_version_ordinal" in indexes

        await connection.execute(
            text(
                """
                INSERT INTO organizations (id, name, slug, created_at, updated_at)
                VALUES (:id, 'Acme', 'acme', now(), now())
                """
            ),
            {"id": org_id},
        )
        await connection.execute(
            text(
                """
                INSERT INTO users
                (id, email, full_name, password_hash, is_active, is_superuser,
                 created_at, updated_at)
                VALUES (:id, 'ada@example.com', 'Ada', 'hash', true, false, now(), now())
                """
            ),
            {"id": user_id},
        )
        for wid, slug in [(workspace_id, "main"), (other_workspace_id, "other")]:
            await connection.execute(
                text(
                    """
                    INSERT INTO workspaces (id, organization_id, name, slug, created_at, updated_at)
                    VALUES (:id, :org_id, :name, :slug, now(), now())
                    """
                ),
                {"id": wid, "org_id": org_id, "name": slug.title(), "slug": slug},
            )
        await connection.execute(
            text(
                """
                INSERT INTO documents
                (id, workspace_id, title, status, created_by, created_at, updated_at)
                VALUES (:id, :workspace_id, 'Atlas', 'ready', :user_id, now(), now())
                """
            ),
            {"id": document_id, "workspace_id": workspace_id, "user_id": user_id},
        )
        await connection.execute(
            text(
                """
                INSERT INTO document_versions
                (id, document_id, version_number, filename, mime_type, size_bytes,
                 checksum_sha256, storage_key, metadata_json, created_at, updated_at)
                VALUES
                (:id, :document_id, 1, 'atlas.txt', 'text/plain', 12,
                 :checksum, :storage_key, '{}', now(), now())
                """
            ),
            {
                "id": version_id,
                "document_id": document_id,
                "checksum": "a" * 64,
                "storage_key": f"approved/{workspace_id}/atlas.txt",
            },
        )
        await connection.execute(
            text(
                """
                INSERT INTO chunks
                (id, document_version_id, workspace_id, ordinal, content, token_count,
                 metadata_json, embedding, created_at, updated_at)
                VALUES
                (:id, :version_id, :workspace_id, 0, 'Atlas launch date', 3,
                 '{}', :embedding, now(), now()),
                (:other_id, :version_id, :other_workspace_id, 1, 'Other tenant text', 3,
                 '{}', :other_embedding, now(), now())
                """
            ),
            {
                "id": chunk_id,
                "other_id": other_chunk_id,
                "version_id": version_id,
                "workspace_id": workspace_id,
                "other_workspace_id": other_workspace_id,
                "embedding": str(vector),
                "other_embedding": str(other_vector),
            },
        )
        nearest = (
            await connection.execute(
                text(
                    """
                    SELECT id
                    FROM chunks
                    WHERE workspace_id = :workspace_id
                      AND document_version_id = :version_id
                    ORDER BY embedding <=> :query_vector
                    LIMIT 1
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "version_id": version_id,
                    "query_vector": str(vector),
                },
            )
        ).scalar_one()
        assert nearest == chunk_id

        tenant_count = await connection.scalar(
            text("SELECT count(*) FROM chunks WHERE workspace_id = :workspace_id"),
            {"workspace_id": workspace_id},
        )
        assert tenant_count == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_rollback_and_connection_recovery(migrated_postgres_url: str):
    engine = create_async_engine(migrated_postgres_url, pool_pre_ping=True)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        marker = f"rollback-{uuid4()}"
        await connection.execute(
            text(
                """
                INSERT INTO organizations (id, name, slug, created_at, updated_at)
                VALUES (:id, 'Rollback', :slug, now(), now())
                """
            ),
            {"id": uuid4(), "slug": marker},
        )
        await transaction.rollback()
        count = await connection.scalar(
            text("SELECT count(*) FROM organizations WHERE slug = :slug"), {"slug": marker}
        )
        assert count == 0
        assert await connection.scalar(text("SELECT 1")) == 1
    await engine.dispose()
