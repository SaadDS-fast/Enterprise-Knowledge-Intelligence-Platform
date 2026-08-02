from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.rate_limit import RateLimited
from app.api.dependencies.tenancy import Tenant
from app.db.session import get_db
from app.exceptions.base import AppError
from app.models.schemas import SearchRequest, SearchResponse
from app.security.audit import record_audit_event
from app.services.search_service import search_and_answer

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SearchResponse:
    try:
        response = await search_and_answer(
            session,
            workspace_id=tenant.workspace_id,
            query=payload.query,
            top_k=payload.top_k,
            document_ids=payload.document_ids,
            request_id=getattr(request.state, "request_id", None),
            passport_actor_id=tenant.user_id,
        )
    except AppError as exc:
        await record_audit_event(
            session,
            action="search.denied",
            resource_type="search",
            actor_user_id=tenant.user_id,
            workspace_id=tenant.workspace_id,
            request_id=getattr(request.state, "request_id", None),
            details={
                "outcome": exc.code.value,
                "selected_document_scope": bool(payload.document_ids),
            },
        )
        await session.commit()
        raise
    await record_audit_event(
        session,
        action="search.selected_document" if payload.document_ids else "search.executed",
        resource_type="search",
        actor_user_id=tenant.user_id,
        workspace_id=tenant.workspace_id,
        request_id=getattr(request.state, "request_id", None),
        details={
            "outcome": response.outcome,
            "selected_document_scope": bool(payload.document_ids),
            "generation_used": response.generation_used,
        },
    )
    await session.commit()
    return response
