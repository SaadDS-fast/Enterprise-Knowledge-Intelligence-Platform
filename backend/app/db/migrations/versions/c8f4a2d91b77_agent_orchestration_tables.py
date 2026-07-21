"""add controlled agent orchestration tables

Revision ID: c8f4a2d91b77
Revises: b4a8e9d12f31
Create Date: 2026-07-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8f4a2d91b77"
down_revision: str | None = "b4a8e9d12f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_state", sa.String(length=40), nullable=False),
        sa.Column("input_query", sa.Text(), nullable=False),
        sa.Column("safe_plan_summary", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_current_state"), "agent_runs", ["current_state"])
    op.create_index(op.f("ix_agent_runs_error_code"), "agent_runs", ["error_code"])
    op.create_index(op.f("ix_agent_runs_request_id"), "agent_runs", ["request_id"])
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"])
    op.create_index(op.f("ix_agent_runs_tenant_id"), "agent_runs", ["tenant_id"])
    op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"])
    op.create_index(op.f("ix_agent_runs_workspace_id"), "agent_runs", ["workspace_id"])
    op.create_table(
        "agent_steps",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_steps_error_code"), "agent_steps", ["error_code"])
    op.create_index(op.f("ix_agent_steps_run_id"), "agent_steps", ["run_id"])
    op.create_index(op.f("ix_agent_steps_state"), "agent_steps", ["state"])
    op.create_index(op.f("ix_agent_steps_status"), "agent_steps", ["status"])
    op.create_index(op.f("ix_agent_steps_workspace_id"), "agent_steps", ["workspace_id"])
    op.create_table(
        "agent_tool_calls",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["agent_steps.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_tool_calls_error_code"), "agent_tool_calls", ["error_code"])
    op.create_index(op.f("ix_agent_tool_calls_run_id"), "agent_tool_calls", ["run_id"])
    op.create_index(op.f("ix_agent_tool_calls_status"), "agent_tool_calls", ["status"])
    op.create_index(op.f("ix_agent_tool_calls_step_id"), "agent_tool_calls", ["step_id"])
    op.create_index(op.f("ix_agent_tool_calls_tool_name"), "agent_tool_calls", ["tool_name"])
    op.create_index(op.f("ix_agent_tool_calls_workspace_id"), "agent_tool_calls", ["workspace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_tool_calls_workspace_id"), table_name="agent_tool_calls")
    op.drop_index(op.f("ix_agent_tool_calls_tool_name"), table_name="agent_tool_calls")
    op.drop_index(op.f("ix_agent_tool_calls_step_id"), table_name="agent_tool_calls")
    op.drop_index(op.f("ix_agent_tool_calls_status"), table_name="agent_tool_calls")
    op.drop_index(op.f("ix_agent_tool_calls_run_id"), table_name="agent_tool_calls")
    op.drop_index(op.f("ix_agent_tool_calls_error_code"), table_name="agent_tool_calls")
    op.drop_table("agent_tool_calls")
    op.drop_index(op.f("ix_agent_steps_workspace_id"), table_name="agent_steps")
    op.drop_index(op.f("ix_agent_steps_status"), table_name="agent_steps")
    op.drop_index(op.f("ix_agent_steps_state"), table_name="agent_steps")
    op.drop_index(op.f("ix_agent_steps_run_id"), table_name="agent_steps")
    op.drop_index(op.f("ix_agent_steps_error_code"), table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_index(op.f("ix_agent_runs_workspace_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_tenant_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_request_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_error_code"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_current_state"), table_name="agent_runs")
    op.drop_table("agent_runs")
