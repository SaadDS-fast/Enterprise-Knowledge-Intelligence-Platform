from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.jobs import get_job


async def fetch_job(session: AsyncSession, workspace_id: UUID, job_id: UUID):
    return await get_job(session, workspace_id, job_id)
