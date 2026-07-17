from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_event import AuditEvent


async def record_audit_event(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    actor_user_id: UUID | None = None,
    workspace_id: UUID | None = None,
    resource_id: str | None = None,
    request_id: str | None = None,
    details: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        workspace_id=workspace_id,
        resource_id=resource_id,
        request_id=request_id,
        details_json=details or {},
    )
    session.add(event)
    await session.flush()
    return event
