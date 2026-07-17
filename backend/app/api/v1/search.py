from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.rate_limit import RateLimited
from app.api.dependencies.tenancy import Tenant
from app.db.session import get_db
from app.models.schemas import SearchRequest, SearchResponse
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
    return await search_and_answer(
        session,
        workspace_id=tenant.workspace_id,
        query=payload.query,
        top_k=payload.top_k,
        document_ids=payload.document_ids,
        request_id=getattr(request.state, "request_id", None),
    )
