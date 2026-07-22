from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResearchJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_jobs"
    tenant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    agent_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    request_id: Mapped[str | None] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    current_state: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    stage: Mapped[str] = mapped_column(String(80), default="pending")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    authorized_document_scope: Mapped[list | None] = mapped_column(JSON)
    external_sources_allowed: Mapped[bool] = mapped_column(default=False, nullable=False)
    requested_formats: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    verified_citation_count: Mapped[int] = mapped_column(Integer, default=0)
    artifact_refs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), index=True)
    report_markdown: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str | None] = mapped_column(String(160), index=True)
    pipeline_version: Mapped[str] = mapped_column(String(40), default="research-v1", nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "workspace_id",
            "user_id",
            "idempotency_key",
            name="uq_research_jobs_scoped_idempotency_key",
        ),
    )


class ResearchArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "research_artifacts"
    research_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    format: Mapped[str] = mapped_column(String(20), index=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(180), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(40), default="research-v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="available", index=True)
