from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.tenancy import Tenant
from app.db.models import ResearchJob
from app.db.session import get_db
from app.exceptions.base import NotFoundError
from app.models.schemas import ResearchRead, ResearchRequest
from app.services.research_service import create_research_job

router = APIRouter()


@router.post("", response_model=ResearchRead, status_code=201)
async def create(
    payload: ResearchRequest, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> ResearchRead:
    return ResearchRead.model_validate(
        await create_research_job(
            session,
            workspace_id=tenant.workspace_id,
            user_id=tenant.user_id,
            question=payload.question,
        )
    )


@router.get("", response_model=list[ResearchRead])
async def list_research(
    tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> list[ResearchRead]:
    rows = (
        await session.scalars(
            select(ResearchJob)
            .where(ResearchJob.workspace_id == tenant.workspace_id)
            .order_by(ResearchJob.created_at.desc())
            .limit(50)
        )
    ).all()
    return [ResearchRead.model_validate(row) for row in rows]


@router.get("/{job_id}", response_model=ResearchRead)
async def read(
    job_id: UUID, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> ResearchRead:
    item = await session.scalar(
        select(ResearchJob).where(
            ResearchJob.id == job_id, ResearchJob.workspace_id == tenant.workspace_id
        )
    )
    if not item:
        raise NotFoundError("Research job not found")
    return ResearchRead.model_validate(item)
