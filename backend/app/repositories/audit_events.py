from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


async def list_audit_events(
    session: AsyncSession, workspace_id: UUID, limit: int = 100
) -> list[AuditEvent]:
    return list(
        (
            await session.scalars(
                select(AuditEvent)
                .where(AuditEvent.workspace_id == workspace_id)
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
