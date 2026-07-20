"""add pgvector production indexes

Revision ID: b4a8e9d12f31
Revises: af7c7edc7f57
Create Date: 2026-07-20 16:43:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4a8e9d12f31"
down_revision: str | None = "af7c7edc7f57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_index(
        "ix_documents_workspace_status_updated",
        "documents",
        ["workspace_id", "status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_document_versions_document_version_desc",
        "document_versions",
        ["document_id", "version_number"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_workspace_version_ordinal",
        "chunks",
        ["workspace_id", "document_version_id", "ordinal"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_workspace_status_updated",
        "ingestion_jobs",
        ["workspace_id", "status", "updated_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_embedding_cosine_ivfflat
        ON chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    if not _is_postgresql():
        return

    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_cosine_ivfflat")
    op.drop_index("ix_ingestion_jobs_workspace_status_updated", table_name="ingestion_jobs")
    op.drop_index("ix_chunks_workspace_version_ordinal", table_name="chunks")
    op.drop_index("ix_document_versions_document_version_desc", table_name="document_versions")
    op.drop_index("ix_documents_workspace_status_updated", table_name="documents")
