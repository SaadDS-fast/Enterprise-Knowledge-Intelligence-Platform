from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IngestionJob


async def get_job(session: AsyncSession, workspace_id: UUID, job_id: UUID) -> IngestionJob | None:
    return await session.scalar(
        select(IngestionJob).where(
            IngestionJob.id == job_id, IngestionJob.workspace_id == workspace_id
        )
    )


async def list_jobs(
    session: AsyncSession, workspace_id: UUID, limit: int = 50
) -> list[IngestionJob]:
    return list(
        (
            await session.scalars(
                select(IngestionJob)
                .where(IngestionJob.workspace_id == workspace_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
