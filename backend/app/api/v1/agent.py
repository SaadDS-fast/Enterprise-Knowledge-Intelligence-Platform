from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.enums import AgentErrorCode
from app.agents.errors import AgentBudgetError, AgentCancelledError, AgentPolicyError
from app.agents.orchestrator import AgentOrchestrator, read_agent_run
from app.agents.schemas import (
    AgentFeatureDisabledResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentRunRead,
)
from app.api.dependencies.rate_limit import RateLimited
from app.api.dependencies.tenancy import Tenant
from app.core.config import settings
from app.db.session import get_db
from app.exceptions.base import AppError, NotFoundError
from app.exceptions.codes import ErrorCode

router = APIRouter()


@router.post("/query", response_model=AgentQueryResponse | AgentFeatureDisabledResponse)
async def agent_query(
    payload: AgentQueryRequest,
    request: Request,
    tenant: Tenant,
    _rate: RateLimited,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentQueryResponse | JSONResponse:
    if not settings.agentic_rag_enabled:
        return JSONResponse(
            status_code=403,
            content=AgentFeatureDisabledResponse().model_dump(),
        )
    try:
        return await AgentOrchestrator().run(
            session,
            tenant=tenant,
            payload=payload,
            request_id=getattr(request.state, "request_id", None),
        )
    except AgentCancelledError as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, 499) from exc
    except AgentBudgetError as exc:
        status_code = 408 if exc.code is AgentErrorCode.TIMEOUT else 400
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, status_code) from exc
    except AgentPolicyError as exc:
        raise AppError(ErrorCode.VALIDATION_FAILED, exc.message, 400) from exc


@router.get("/runs/{run_id}", response_model=AgentRunRead)
async def agent_run(
    run_id: UUID,
    tenant: Tenant,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentRunRead:
    result = await read_agent_run(session, workspace_id=tenant.workspace_id, run_id=run_id)
    if not result:
        raise NotFoundError("Agent run not found")
    return result
