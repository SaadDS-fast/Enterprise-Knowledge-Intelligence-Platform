from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EvaluationRun
from app.evaluation.generation_metrics import exact_match, token_f1
from app.models.schemas import EvaluationCase
from app.services.search_service import search_and_answer


async def run_evaluation(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    name: str,
    cases: list[EvaluationCase],
) -> EvaluationRun:
    run = EvaluationRun(
        workspace_id=workspace_id,
        user_id=user_id,
        name=name,
        status="running",
        config_json={"cases": [case.model_dump() for case in cases]},
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    exact, f1, answered = [], [], 0
    for case in cases:
        result = await search_and_answer(session, workspace_id=workspace_id, query=case.question)
        exact.append(exact_match(result.answer, case.expected_answer))
        f1.append(token_f1(result.answer, case.expected_answer))
        answered += int(not result.abstained)
    run.metrics_json = {
        "cases": len(cases),
        "exact_match": sum(exact) / len(exact),
        "token_f1": sum(f1) / len(f1),
        "answer_rate": answered / len(cases),
    }
    run.status = "completed"
    await session.commit()
    await session.refresh(run)
    return run
