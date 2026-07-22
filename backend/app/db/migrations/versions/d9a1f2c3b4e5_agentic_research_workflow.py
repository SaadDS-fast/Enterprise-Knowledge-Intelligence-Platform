"""add controlled agentic research workflow

Revision ID: d9a1f2c3b4e5
Revises: c8f4a2d91b77
Create Date: 2026-07-22 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9a1f2c3b4e5"
down_revision: str | None = "c8f4a2d91b77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("research_jobs") as batch_op:
        batch_op.add_column(sa.Column("tenant_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("agent_run_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=80), nullable=True))
        batch_op.add_column(
            sa.Column(
                "current_state",
                sa.String(length=40),
                nullable=False,
                server_default="PENDING",
            )
        )
        batch_op.add_column(
            sa.Column("stage", sa.String(length=80), nullable=False, server_default="pending")
        )
        batch_op.add_column(
            sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("authorized_document_scope", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "external_sources_allowed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("requested_formats", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(
            sa.Column("source_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("verified_citation_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("artifact_refs", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("error_code", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column(
                "pipeline_version",
                sa.String(length=40),
                nullable=False,
                server_default="research-v1",
            )
        )
        batch_op.create_foreign_key(
            op.f("fk_research_jobs_tenant_id_organizations"),
            "organizations",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            op.f("fk_research_jobs_agent_run_id_agent_runs"),
            "agent_runs",
            ["agent_run_id"],
            ["id"],
        )
        batch_op.create_index(op.f("ix_research_jobs_tenant_id"), ["tenant_id"])
        batch_op.create_index(op.f("ix_research_jobs_agent_run_id"), ["agent_run_id"])
        batch_op.create_index(op.f("ix_research_jobs_request_id"), ["request_id"])
        batch_op.create_index(op.f("ix_research_jobs_current_state"), ["current_state"])
        batch_op.create_index(op.f("ix_research_jobs_error_code"), ["error_code"])
        batch_op.create_index(op.f("ix_research_jobs_idempotency_key"), ["idempotency_key"])
        batch_op.create_unique_constraint(
            "uq_research_jobs_scoped_idempotency_key",
            ["tenant_id", "workspace_id", "user_id", "idempotency_key"],
        )

    op.create_table(
        "research_artifacts",
        sa.Column("research_job_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=180), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_artifacts_format"), "research_artifacts", ["format"])
    op.create_index(
        op.f("ix_research_artifacts_research_job_id"),
        "research_artifacts",
        ["research_job_id"],
    )
    op.create_index(op.f("ix_research_artifacts_status"), "research_artifacts", ["status"])
    op.create_index(
        op.f("ix_research_artifacts_workspace_id"), "research_artifacts", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_research_artifacts_workspace_id"), table_name="research_artifacts")
    op.drop_index(op.f("ix_research_artifacts_status"), table_name="research_artifacts")
    op.drop_index(op.f("ix_research_artifacts_research_job_id"), table_name="research_artifacts")
    op.drop_index(op.f("ix_research_artifacts_format"), table_name="research_artifacts")
    op.drop_table("research_artifacts")
    with op.batch_alter_table("research_jobs") as batch_op:
        batch_op.drop_constraint("uq_research_jobs_scoped_idempotency_key", type_="unique")
        batch_op.drop_index(op.f("ix_research_jobs_idempotency_key"))
        batch_op.drop_index(op.f("ix_research_jobs_error_code"))
        batch_op.drop_index(op.f("ix_research_jobs_current_state"))
        batch_op.drop_index(op.f("ix_research_jobs_request_id"))
        batch_op.drop_index(op.f("ix_research_jobs_agent_run_id"))
        batch_op.drop_index(op.f("ix_research_jobs_tenant_id"))
        batch_op.drop_constraint(
            op.f("fk_research_jobs_agent_run_id_agent_runs"), type_="foreignkey"
        )
        batch_op.drop_constraint(
            op.f("fk_research_jobs_tenant_id_organizations"), type_="foreignkey"
        )
        for column in (
            "pipeline_version",
            "idempotency_key",
            "cancelled_at",
            "completed_at",
            "started_at",
            "error_code",
            "artifact_refs",
            "verified_citation_count",
            "source_count",
            "requested_formats",
            "external_sources_allowed",
            "authorized_document_scope",
            "progress_percent",
            "stage",
            "current_state",
            "request_id",
            "agent_run_id",
            "tenant_id",
        ):
            batch_op.drop_column(column)
