from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.tenancy import Tenant
from app.db.models import EvaluationRun
from app.db.session import get_db
from app.models.schemas import EvaluationRead, EvaluationRequest
from app.services.evaluation_service import run_evaluation

router = APIRouter()


@router.post("", response_model=EvaluationRead, status_code=201)
async def create(
    payload: EvaluationRequest, tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> EvaluationRead:
    return EvaluationRead.model_validate(
        await run_evaluation(
            session,
            workspace_id=tenant.workspace_id,
            user_id=tenant.user_id,
            name=payload.name,
            cases=payload.cases,
            pipeline=payload.pipeline,
        )
    )


@router.get("", response_model=list[EvaluationRead])
async def list_runs(
    tenant: Tenant, session: Annotated[AsyncSession, Depends(get_db)]
) -> list[EvaluationRead]:
    rows = (
        await session.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.workspace_id == tenant.workspace_id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(50)
        )
    ).all()
    return [EvaluationRead.model_validate(row) for row in rows]
