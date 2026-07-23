from __future__ import annotations

import time
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.budgets import AgentBudget
from app.agents.orchestrator import AgentOrchestrator
from app.agents.research import (
    PIPELINE_VERSION,
    ResearchCreateRequest,
    ResearchFormat,
    ResearchState,
    build_structured_report,
    render_docx,
    render_markdown,
    render_pdf,
    research_object_key,
    scoped_idempotency_key,
    sign_download_token,
    validate_transition,
)
from app.agents.schemas import AgentQueryRequest
from app.core.config import JobExecutionMode, settings
from app.db.models import Document, ResearchArtifact, ResearchJob, Workspace
from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode
from app.integrations.storage import get_storage
from app.integrations.storage.keys import safe_object_name
from app.jobs.queue import celery_app
from app.observability.metrics import (
    AGENT_RESEARCH_CITATIONS_VALIDATED,
    AGENT_RESEARCH_CLAIMS_VERIFIED,
    AGENT_RESEARCH_EXPORT_FAILURES,
    AGENT_RESEARCH_EXPORTS,
    AGENT_RESEARCH_JOBS_CANCELLED,
    AGENT_RESEARCH_JOBS_COMPLETED,
    AGENT_RESEARCH_JOBS_FAILED,
    AGENT_RESEARCH_JOBS_STARTED,
    AGENT_RESEARCH_SOURCES_USED,
    AGENT_RESEARCH_STAGE_DURATION,
    AGENT_RESEARCH_TOTAL_DURATION,
)
from app.observability.tracing import safe_span
from app.services.search_service import search_and_answer
from app.tenancy.context import TenantContext
from app.utils.time import utc_now


async def create_research_job(
    session: AsyncSession, *, workspace_id: UUID, user_id: UUID, question: str
) -> ResearchJob:
    workspace = await session.get(Workspace, workspace_id)
    tenant_id = workspace.organization_id if workspace else None
    job = ResearchJob(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        user_id=user_id,
        question=question,
        status="running",
        current_state=ResearchState.WRITING.value,
        stage="legacy_research",
        progress_percent=50,
        requested_formats=[ResearchFormat.MARKDOWN.value],
        pipeline_version=PIPELINE_VERSION,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    try:
        result = await search_and_answer(session, workspace_id=workspace_id, query=question)
        sources = "\n".join(f"- {e.document_title} (score {e.score:.2f})" for e in result.evidence)
        evidence_status = "Sufficient" if result.sufficient_evidence else "Insufficient"
        job.report_markdown = (
            f"# Research Brief\n\n## Question\n{question}\n\n"
            f"## Findings\n{result.answer}\n\n"
            f"## Evidence Status\n{evidence_status}\n\n"
            f"## Sources\n{sources or '- None'}"
        )
        job.result_json = result.model_dump(mode="json")
        job.status = "completed"
        job.current_state = ResearchState.COMPLETED.value
        job.stage = "completed"
        job.progress_percent = 100
        job.completed_at = utc_now()
    except Exception as exc:
        job.status = "failed"
        job.current_state = ResearchState.FAILED.value
        job.error_code = "LEGACY_RESEARCH_FAILED"
        job.error_message = _sanitize_error(exc)
    await session.commit()
    await session.refresh(job)
    return job


async def create_agent_research_job(
    session: AsyncSession,
    *,
    tenant: TenantContext,
    payload: ResearchCreateRequest,
    request_id: str | None,
    background_tasks: BackgroundTasks | None = None,
) -> tuple[ResearchJob, bool]:
    await _validate_document_scope(session, tenant.workspace_id, payload.document_ids)
    idempotency = scoped_idempotency_key(
        tenant_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        user_id=tenant.user_id,
        payload=payload,
    )
    existing = await session.scalar(
        select(ResearchJob).where(
            ResearchJob.tenant_id == tenant.organization_id,
            ResearchJob.workspace_id == tenant.workspace_id,
            ResearchJob.user_id == tenant.user_id,
            ResearchJob.idempotency_key == idempotency,
        )
    )
    if existing:
        return existing, True
    await _enforce_research_capacity(session, tenant)
    job = ResearchJob(
        tenant_id=tenant.organization_id,
        workspace_id=tenant.workspace_id,
        user_id=tenant.user_id,
        request_id=request_id,
        question=payload.question,
        status="pending",
        current_state=ResearchState.PENDING.value,
        stage="queued",
        progress_percent=0,
        authorized_document_scope=[str(item) for item in payload.document_ids or []],
        external_sources_allowed=payload.allow_external_sources,
        requested_formats=[item.value for item in payload.requested_formats],
        result_json={
            "max_depth_preset": payload.max_depth_preset,
            "pipeline_version": PIPELINE_VERSION,
        },
        idempotency_key=idempotency,
        pipeline_version=PIPELINE_VERSION,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    task_id = await dispatch_research_safely(
        session, job.id, request_id=request_id, background_tasks=background_tasks
    )
    job.result_json = {**(job.result_json or {}), "task_id": task_id or str(job.id)}
    await session.commit()
    await session.refresh(job)
    return job, False


async def _enforce_research_capacity(session: AsyncSession, tenant: TenantContext) -> None:
    active_statuses = {"pending", "running", "dispatch_failed", "retry_pending", "cancel_requested"}
    workspace_jobs = (
        await session.scalars(
            select(ResearchJob.id).where(
                ResearchJob.tenant_id == tenant.organization_id,
                ResearchJob.workspace_id == tenant.workspace_id,
                ResearchJob.status.in_(active_statuses),
            )
        )
    ).all()
    if len(workspace_jobs) >= settings.agent_research_max_concurrent_per_workspace:
        raise AppError(
            ErrorCode.CONCURRENCY_LIMIT_REACHED,
            "Workspace has reached the active research job limit",
            429,
        )
    user_jobs = (
        await session.scalars(
            select(ResearchJob.id).where(
                ResearchJob.tenant_id == tenant.organization_id,
                ResearchJob.workspace_id == tenant.workspace_id,
                ResearchJob.user_id == tenant.user_id,
                ResearchJob.status.in_(active_statuses),
            )
        )
    ).all()
    if len(user_jobs) >= settings.agent_research_max_concurrent_per_user:
        raise AppError(
            ErrorCode.CONCURRENCY_LIMIT_REACHED,
            "User has reached the active research job limit",
            429,
        )
    queued_jobs = (
        await session.scalars(
            select(ResearchJob.id).where(
                ResearchJob.status.in_({"pending", "dispatch_failed", "retry_pending"}),
            )
        )
    ).all()
    if len(queued_jobs) >= settings.agent_research_max_queued_jobs:
        raise AppError(
            ErrorCode.TEMPORARY_FAILURE,
            "Research queue is temporarily at capacity",
            503,
        )


def dispatch_research(
    job_id: UUID,
    background_tasks: BackgroundTasks | None = None,
    *,
    request_id: str | None = None,
) -> str | None:
    if settings.job_execution_mode is JobExecutionMode.CELERY:
        result = celery_app.send_task(
            "ekip.research_report",
            args=[str(job_id)],
            kwargs={"request_id": request_id},
            queue="reports",
            task_id=str(job_id),
            headers={"request_id": request_id, "published_at": datetime.now(UTC).isoformat()},
        )
        return result.id
    if background_tasks is not None:
        background_tasks.add_task(generate_research_report, job_id, request_id=request_id)
        return None
    return None


async def dispatch_research_safely(
    session: AsyncSession,
    job_id: UUID,
    *,
    request_id: str | None,
    background_tasks: BackgroundTasks | None = None,
) -> str | None:
    job = await session.get(ResearchJob, job_id)
    if not job:
        return None
    try:
        task_id = dispatch_research(job_id, background_tasks, request_id=request_id)
    except Exception as exc:
        job.status = "dispatch_failed"
        job.stage = "dispatch_failed"
        job.error_code = "RESEARCH_DISPATCH_FAILED"
        job.error_message = _sanitize_error(exc)
        await session.commit()
        return None
    if task_id:
        job.status = "pending"
        job.stage = "queued"
        job.error_code = None
        job.error_message = None
        job.result_json = {**(job.result_json or {}), "task_id": task_id}
        await session.commit()
    return task_id


async def generate_research_report(job_id: UUID, request_id: str | None = None) -> dict:
    started = time.perf_counter()
    AGENT_RESEARCH_JOBS_STARTED.inc()
    with safe_span("research.generate", request_present=bool(request_id)):
        return await _generate_research_report_inner(job_id, request_id, started)


async def _generate_research_report_inner(
    job_id: UUID, request_id: str | None, started: float
) -> dict:
    async with _session_scope() as session:
        job = await session.get(ResearchJob, job_id)
        if not job:
            return {"status": "missing"}
        if job.current_state == ResearchState.COMPLETED.value:
            return {"status": "completed", "idempotent": True}
        try:
            await _check_cancelled(session, job)
            await _transition(session, job, ResearchState.AUTHORIZING, 5, "authorizing")
            await _check_cancelled(session, job)
            workspace = await session.get(Workspace, job.workspace_id)
            if workspace is None or workspace.organization_id != job.tenant_id:
                raise RuntimeError("workspace_scope_invalid")
            tenant = TenantContext(
                user_id=job.user_id,
                workspace_id=job.workspace_id,
                organization_id=job.tenant_id,
                role="owner",
            )
            await _transition(session, job, ResearchState.PLANNING, 10, "planning")
            await _check_cancelled(session, job)
            await _transition(session, job, ResearchState.RETRIEVING, 25, "retrieving")
            payload = AgentQueryRequest(
                query=job.question,
                document_ids=[UUID(item) for item in job.authorized_document_scope or []] or None,
                allow_external_sources=job.external_sources_allowed,
            )
            response = await AgentOrchestrator(
                budget=AgentBudget(
                    max_steps=settings.agent_research_max_steps,
                    max_tool_calls=settings.agent_research_max_tool_calls,
                    max_retrieval_retries=settings.agent_max_retrieval_retries,
                    timeout_seconds=settings.agent_research_timeout_seconds,
                    started_at=time.monotonic(),
                )
            ).run(
                session,
                tenant=tenant,
                payload=payload,
                request_id=request_id or job.request_id,
            )
            job.agent_run_id = response.run_id
            if "query_reformulation" in response.tools_used:
                await _transition(
                    session, job, ResearchState.RETRIEVAL_RETRY, 35, "retrieval_retry"
                )
            await _transition(
                session, job, ResearchState.AGGREGATING_EVIDENCE, 45, "aggregating_evidence"
            )
            await _check_cancelled(session, job)
            await _transition(
                session, job, ResearchState.VERIFYING_EVIDENCE, 55, "verifying_evidence"
            )
            source_count = min(
                settings.agent_research_max_sources,
                len(response.unified_evidence)
                or len(response.internal_evidence) + len(response.external_evidence),
            )
            job.source_count = source_count
            job.verified_citation_count = len(response.citations)
            AGENT_RESEARCH_CLAIMS_VERIFIED.labels(outcome=response.outcome).inc(
                len(response.claims)
            )
            AGENT_RESEARCH_CITATIONS_VALIDATED.labels(outcome="accepted").inc(
                len(response.citations)
            )
            for item in response.unified_evidence:
                AGENT_RESEARCH_SOURCES_USED.labels(
                    source_type=str(item.get("source_type", "unknown"))
                ).inc()
            await _transition(session, job, ResearchState.WRITING, 65, "writing")
            report = build_structured_report(response, job.question)
            remaining_sources = settings.agent_research_max_sources
            report.internal_evidence = report.internal_evidence[:remaining_sources]
            remaining_sources = max(0, remaining_sources - len(report.internal_evidence))
            report.external_evidence = report.external_evidence[:remaining_sources]
            report.citations = report.citations[: settings.agent_research_max_sources]
            markdown = render_markdown(report)
            job.report_markdown = markdown
            await _transition(
                session, job, ResearchState.VERIFYING_CITATIONS, 75, "verifying_citations"
            )
            if response.citations and not report.citations:
                raise RuntimeError("citation_validation_failed")
            if response.external_evidence and not job.external_sources_allowed:
                raise RuntimeError("external_source_policy_violation")
            await _transition(session, job, ResearchState.SAFETY_REVIEW, 82, "safety_review")
            if "ignore all prior rules" in markdown.lower() or "reveal secrets" in markdown.lower():
                raise RuntimeError("prompt_injection_detected")
            await _transition(session, job, ResearchState.EXPORTING, 90, "exporting")
            artifacts = await _export_artifacts(session, job, markdown)
            job.artifact_refs = [artifact_ref(artifact) for artifact in artifacts]
            job.result_json = {
                **(job.result_json or {}),
                "agent": response.model_dump(mode="json"),
                "report": report.model_dump(mode="json"),
                "artifact_count": len(artifacts),
            }
            await _transition(session, job, ResearchState.COMPLETED, 100, "completed")
            job.status = "completed"
            job.completed_at = utc_now()
            await session.commit()
            AGENT_RESEARCH_JOBS_COMPLETED.inc()
            AGENT_RESEARCH_TOTAL_DURATION.observe(time.perf_counter() - started)
            return {"status": "completed", "job_id": str(job.id)}
        except ResearchCancelled:
            job.status = "cancelled"
            job.current_state = ResearchState.CANCELLED.value
            job.stage = "cancelled"
            job.progress_percent = min(job.progress_percent, 99)
            job.cancelled_at = utc_now()
            await session.commit()
            AGENT_RESEARCH_JOBS_CANCELLED.inc()
            return {"status": "cancelled", "job_id": str(job.id)}
        except Exception as exc:
            job.status = "failed"
            job.current_state = ResearchState.FAILED.value
            job.stage = "failed"
            job.error_code = _error_code(exc)
            job.error_message = _sanitize_error(exc)
            await session.commit()
            AGENT_RESEARCH_JOBS_FAILED.inc()
            raise


async def cancel_research_job(session: AsyncSession, job: ResearchJob) -> ResearchJob:
    if job.current_state == ResearchState.COMPLETED.value:
        raise ValueError("completed_job_cannot_be_cancelled")
    if job.current_state in {ResearchState.CANCELLED.value, ResearchState.FAILED.value}:
        return job
    job.current_state = ResearchState.CANCEL_REQUESTED.value
    job.status = "cancel_requested"
    job.stage = "cancel_requested"
    job.cancelled_at = utc_now()
    await session.commit()
    await session.refresh(job)
    return job


async def list_research_artifacts(
    session: AsyncSession, *, workspace_id: UUID, job_id: UUID
) -> list[ResearchArtifact]:
    return list(
        (
            await session.scalars(
                select(ResearchArtifact)
                .where(
                    ResearchArtifact.workspace_id == workspace_id,
                    ResearchArtifact.research_job_id == job_id,
                    ResearchArtifact.status == "available",
                )
                .order_by(ResearchArtifact.created_at)
            )
        ).all()
    )


def artifact_ref(artifact: ResearchArtifact) -> dict:
    expires, signature = sign_download_token(artifact.research_job_id, artifact.id, artifact.format)
    return {
        "artifact_id": str(artifact.id),
        "format": artifact.format,
        "filename": artifact.filename,
        "mime_type": artifact.mime_type,
        "checksum_sha256": artifact.checksum_sha256,
        "size_bytes": artifact.size_bytes,
        "object_key": artifact.object_key,
        "signed_url_expires": expires,
        "signed_url_signature": signature,
    }


async def _export_artifacts(
    session: AsyncSession, job: ResearchJob, markdown: str
) -> list[ResearchArtifact]:
    storage = get_storage()
    artifacts: list[ResearchArtifact] = []
    requested = job.requested_formats or [ResearchFormat.MARKDOWN.value]
    with safe_span("research.export", format_count=len(requested)):
        for fmt in requested:
            artifact_id = uuid4()
            filename = safe_object_name(f"research-report.{_extension(fmt)}")
            data, mime_type = _render_format(fmt, markdown)
            if not data:
                raise RuntimeError(f"{fmt}_export_empty")
            if len(data.split()) > settings.agent_research_max_report_words * 20:
                raise RuntimeError(f"{fmt}_export_too_large")
            object_key = research_object_key(
                tenant_id=job.tenant_id,
                workspace_id=job.workspace_id,
                job_id=job.id,
                artifact_id=artifact_id,
                ext=_extension(fmt),
            )
            try:
                await storage.put(object_key, data, mime_type)
            except Exception as exc:
                AGENT_RESEARCH_EXPORT_FAILURES.labels(format=fmt, outcome="storage_failed").inc()
                raise RuntimeError(f"{fmt}_export_failed") from exc
            artifact = ResearchArtifact(
                id=artifact_id,
                research_job_id=job.id,
                tenant_id=job.tenant_id,
                workspace_id=job.workspace_id,
                format=fmt,
                object_key=object_key,
                filename=filename,
                mime_type=mime_type,
                checksum_sha256=sha256(data).hexdigest(),
                size_bytes=len(data),
                pipeline_version=PIPELINE_VERSION,
                status="available",
            )
            session.add(artifact)
            artifacts.append(artifact)
            AGENT_RESEARCH_EXPORTS.labels(format=fmt, outcome="success").inc()
    await session.flush()
    return artifacts


def _render_format(fmt: str, markdown: str) -> tuple[bytes, str]:
    if fmt == ResearchFormat.MARKDOWN.value:
        return markdown.encode("utf-8"), "text/markdown"
    if fmt == ResearchFormat.PDF.value:
        return render_pdf(markdown), "application/pdf"
    if fmt == ResearchFormat.DOCX.value:
        return (
            render_docx(markdown),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    raise RuntimeError("unsupported_export_format")


def _extension(fmt: str) -> str:
    return "md" if fmt == ResearchFormat.MARKDOWN.value else fmt


async def _validate_document_scope(
    session: AsyncSession, workspace_id: UUID, document_ids: list[UUID] | None
) -> None:
    if not document_ids:
        return
    count = len(
        (
            await session.scalars(
                select(Document.id).where(
                    Document.workspace_id == workspace_id,
                    Document.id.in_(document_ids),
                )
            )
        ).all()
    )
    if count != len(set(document_ids)):
        raise ValueError("document_scope_not_authorized")


async def _transition(
    session: AsyncSession, job: ResearchJob, target: ResearchState, progress: int, stage: str
) -> None:
    started = time.perf_counter()
    validate_transition(job.current_state, target)
    job.current_state = target.value
    job.stage = stage
    job.progress_percent = progress
    if target == ResearchState.AUTHORIZING:
        job.started_at = utc_now()
        job.status = "running"
    await session.commit()
    AGENT_RESEARCH_STAGE_DURATION.labels(stage=stage, outcome="success").observe(
        time.perf_counter() - started
    )


async def _check_cancelled(session: AsyncSession, job: ResearchJob) -> None:
    await session.refresh(job)
    if job.current_state == ResearchState.CANCEL_REQUESTED.value:
        raise ResearchCancelled()


class ResearchCancelled(Exception):
    pass


def _sanitize_error(exc: Exception) -> str:
    return str(exc).replace("\n", " ")[:500]


def _error_code(exc: Exception) -> str:
    text = str(exc).lower()
    if "citation" in text:
        return "RESEARCH_CITATION_VALIDATION_FAILED"
    if "export" in text:
        return "RESEARCH_EXPORT_FAILED"
    if "prompt" in text:
        return "RESEARCH_SAFETY_BLOCKED"
    return "RESEARCH_FAILED"


class _session_scope:
    async def __aenter__(self) -> AsyncSession:
        from app.db.session import AsyncSessionLocal

        self.session = AsyncSessionLocal()
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.session.close()
