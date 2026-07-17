from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedPrincipal, get_current_principal
from app.core.config import settings
from app.db.session import get_db
from app.exceptions.base import ForbiddenError, NotFoundError
from app.repositories.workspaces import get_membership, get_workspace
from app.tenancy.context import TenantContext


async def get_tenant_context(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db)],
    workspace_header: Annotated[str | None, Header(alias=settings.tenant_header)] = None,
) -> TenantContext:
    try:
        workspace_id = (
            UUID(workspace_header) if workspace_header else principal.default_workspace_id
        )
    except ValueError as exc:
        raise NotFoundError("Invalid workspace identifier") from exc
    membership = await get_membership(session, principal.user.id, workspace_id)
    if not membership:
        raise ForbiddenError("You are not a member of this workspace")
    workspace = await get_workspace(session, workspace_id)
    if not workspace:
        raise NotFoundError("Workspace not found")
    return TenantContext(
        user_id=principal.user.id,
        workspace_id=workspace.id,
        organization_id=workspace.organization_id,
        role=membership.role,
    )


Tenant = Annotated[TenantContext, Depends(get_tenant_context)]
