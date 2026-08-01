from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentBudgetError, AgentCancelledError, AgentPolicyError
from app.agents.orchestrator import AgentOrchestrator, read_agent_run
from app.agents.research import (
    ResearchCreateRequest,
    ResearchCreateResponse,
    ResearchJobRead,
    verify_download_token,
)
from app.agents.schemas import (
    AgentFeatureDisabledResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentRunRead,
)
from app.api.dependencies.rate_limit import RateLimited
from app.api.dependencies.tenancy import Tenant
from app.core.config import settings
from app.db.models import ResearchArtifact, ResearchJob
from app.db.session import get_db
from app.exceptions.base import AppError, ConflictError, ForbiddenError, NotFoundError
from app.exceptions.codes import ErrorCode
from app.integrations.storage import get_storage
from app.observability.tracing import safe_span
from app.security.audit import record_audit_event
from app.services.research_service import (
    artifact_ref,
    cancel_research_job,
    create_agent_research_job,
    list_research_artifacts,
)

router = APIRouter()


@router.post("/query", response_model=AgentQueryResponse | AgentFeatureDisabledResponse)
async def agent_query(
    payload: AgentQueryRequest,
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentQueryResponse | JSONResponse:
    if not settings.agentic_rag_enabled:
        return JSONResponse(
            status_code=403,
            content=AgentFeatureDisabledResponse().model_dump(),
        )
    try:
        with safe_span(
            "agent.query", endpoint="/agent/query", external=payload.allow_external_sources
        ):
            return await AgentOrchestrator().run(
                session,
                tenant=tenant,
                payload=payload,
                request_id=getattr(request.state, "request_id", None),
            )
    except AgentCancelledError as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, 499) from exc
    except AgentBudgetError as exc:
        status_code = 408 if exc.code is AgentErrorCode.TIMEOUT else 400
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, status_code) from exc
    except AgentPolicyError as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, 400) from exc


@router.post("/research", response_model=ResearchCreateResponse, status_code=202)
async def create_research_report(
    payload: ResearchCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchCreateResponse | JSONResponse:
    if not settings.agent_research_enabled:
        return JSONResponse(
            status_code=403,
            content={
                "enabled": False,
                "message": (
                    "Agentic research is disabled. Set AGENT_RESEARCH_ENABLED=true to enable it."
                ),
                "code": "AGENT_RESEARCH_FEATURE_DISABLED",
            },
        )
    if payload.allow_external_sources and not settings.agent_research_external_sources_default:
        raise ForbiddenError("External sources are not enabled for research reports")
    try:
        with safe_span(
            "research.create",
            endpoint="/agent/research",
            external=payload.allow_external_sources,
            format_count=len(payload.requested_formats),
        ):
            job, replayed = await create_agent_research_job(
                session,
                tenant=tenant,
                payload=payload,
                request_id=getattr(request.state, "request_id", None),
                background_tasks=background_tasks,
            )
    except ValueError as exc:
        await record_audit_event(
            session,
            action="research.denied",
            resource_type="research_job",
            actor_user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            request_id=getattr(request.state, "request_id", None),
            details={"outcome": "document_scope_denied"},
        )
        await session.commit()
        raise ForbiddenError("Document scope is not authorized") from exc
    await record_audit_event(
        session,
        action="research.created",
        resource_type="research_job",
        actor_user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        resource_id=str(job.id),
        request_id=getattr(request.state, "request_id", None),
        details={"outcome": "replayed" if replayed else "accepted"},
    )
    await session.commit()
    return ResearchCreateResponse(
        job_id=job.id,
        status=job.status,
        current_state=job.current_state,
        idempotent_replay=replayed,
    )


@router.get("/research", response_model=list[ResearchJobRead])
async def list_research_reports(
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ResearchJobRead]:
    jobs = (
        await session.scalars(
            select(ResearchJob)
            .where(
                ResearchJob.tenant_id == tenant.organization_id,
                ResearchJob.workspace_id == tenant.workspace_id,
            )
            .order_by(ResearchJob.created_at.desc())
            .limit(50)
        )
    ).all()
    return [ResearchJobRead.model_validate(job) for job in jobs]


@router.get("/research/{job_id}", response_model=ResearchJobRead)
async def read_research_report(
    job_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchJobRead:
    job = await _read_scoped_research_job(session, tenant, job_id)
    return ResearchJobRead.model_validate(job)


@router.post("/research/{job_id}/cancel", response_model=ResearchJobRead)
async def cancel_research_report(
    job_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ResearchJobRead:
    job = await _read_scoped_research_job(session, tenant, job_id)
    try:
        job = await cancel_research_job(session, job)
    except ValueError as exc:
        raise ConflictError("Completed research jobs cannot be cancelled") from exc
    return ResearchJobRead.model_validate(job)


@router.get("/research/{job_id}/artifacts")
async def list_research_report_artifacts(
    job_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    await _read_scoped_research_job(session, tenant, job_id)
    with safe_span("research.artifacts.list", endpoint="/agent/research/artifacts"):
        artifacts = await list_research_artifacts(
            session, workspace_id=tenant.workspace_id, job_id=job_id
        )
    refs = []
    for artifact in artifacts:
        ref = artifact_ref(artifact)
        ref["download_url"] = (
            f"/api/v1/agent/research/{job_id}/download/{artifact.format}"
            f"?artifact_id={artifact.id}"
            f"&expires={ref['signed_url_expires']}"
            f"&signature={ref['signed_url_signature']}"
        )
        ref.pop("object_key", None)
        ref.pop("signed_url_signature", None)
        refs.append(ref)
    return refs


@router.get("/research/{job_id}/download/{format}")
async def download_research_report_artifact(
    job_id: UUID,
    format: str,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
    artifact_id: UUID | None = Query(default=None),
    expires: int | None = Query(default=None),
    signature: str | None = Query(default=None),
) -> Response:
    await _read_scoped_research_job(session, tenant, job_id)
    filters = [
        ResearchArtifact.research_job_id == job_id,
        ResearchArtifact.workspace_id == tenant.workspace_id,
        ResearchArtifact.tenant_id == tenant.organization_id,
        ResearchArtifact.format == format,
        ResearchArtifact.status == "available",
    ]
    if artifact_id:
        filters.append(ResearchArtifact.id == artifact_id)
    artifact = await session.scalar(select(ResearchArtifact).where(*filters).limit(1))
    if not artifact:
        raise NotFoundError("Research artifact not found")
    if expires is not None or signature is not None:
        if expires is None or signature is None:
            raise ForbiddenError("Invalid research artifact signature")
        if not verify_download_token(job_id, artifact.id, artifact.format, expires, signature):
            raise ForbiddenError("Invalid research artifact signature")
    with safe_span(
        "research.artifact.download", endpoint="/agent/research/download", format=format
    ):
        data = await get_storage().get(artifact.object_key)
    return Response(
        content=data,
        media_type=artifact.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )


@router.get("/runs/{run_id}", response_model=AgentRunRead)
async def agent_run(
    run_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRunRead:
    result = await read_agent_run(session, workspace_id=tenant.workspace_id, run_id=run_id)
    if not result:
        raise NotFoundError("Agent run not found")
    return result


async def _read_scoped_research_job(
    session: AsyncSession, tenant: Tenant, job_id: UUID
) -> ResearchJob:
    job = await session.scalar(
        select(ResearchJob).where(
            ResearchJob.id == job_id,
            ResearchJob.tenant_id == tenant.organization_id,
            ResearchJob.workspace_id == tenant.workspace_id,
        )
    )
    if not job:
        raise NotFoundError("Research job not found")
    return job
