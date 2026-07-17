from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Membership, Workspace


async def get_membership(
    session: AsyncSession, user_id: UUID, workspace_id: UUID
) -> Membership | None:
    return await session.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.workspace_id == workspace_id
        )
    )


async def first_membership(session: AsyncSession, user_id: UUID) -> Membership | None:
    return await session.scalar(
        select(Membership).where(Membership.user_id == user_id).order_by(Membership.created_at)
    )


async def get_workspace(session: AsyncSession, workspace_id: UUID) -> Workspace | None:
    return await session.get(Workspace, workspace_id)
