from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.tenancy import Tenant
from app.db.session import get_db
from app.exceptions.base import NotFoundError
from app.models.schemas import JobRead
from app.repositories.jobs import get_job, list_jobs

router = APIRouter()


@router.get("", response_model=list[JobRead])
async def jobs(tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]) -> list[JobRead]:
    return [JobRead.model_validate(item) for item in await list_jobs(session, tenant.workspace_id)]


@router.get("/{job_id}", response_model=JobRead)
async def job(
    job_id: UUID, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> JobRead:
    item = await get_job(session, tenant.workspace_id, job_id)
    if not item:
        raise NotFoundError("Job not found")
    return JobRead.model_validate(item)
