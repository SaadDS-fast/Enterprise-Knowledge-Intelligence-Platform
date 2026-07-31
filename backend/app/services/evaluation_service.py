import re
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
    pipeline: str = "standard_search",
) -> EvaluationRun:
    run = EvaluationRun(
        workspace_id=workspace_id,
        user_id=user_id,
        name=name,
        status="running",
        config_json={"pipeline": pipeline, "cases": [case.model_dump() for case in cases]},
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    exact, value_match, f1, answered, citation_valid, evidence_supported = [], [], [], 0, [], []
    case_results = []
    for case in cases:
        result = await search_and_answer(session, workspace_id=workspace_id, query=case.question)
        response_state = result.response_state
        if response_state is None:
            raise ValueError("canonical_response_state_missing")
        expected = _normalize_value(case.expected_answer)
        actual_value = _normalize_value(result.answer_value or result.answer)
        exact.append(exact_match(actual_value, expected))
        value_match.append(_value_matches(expected, actual_value))
        f1.append(token_f1(actual_value, expected))
        answered += int(response_state.answer is not None)
        citation_valid.append(
            bool(response_state.citation_ids) if response_state.answer is not None else True
        )
        evidence_supported.append(response_state.evidence_decision == "SUFFICIENT")
        case_results.append(
            {
                "pipeline": pipeline,
                "question": case.question,
                "expected_answer": case.expected_answer,
                "actual_answer": result.answer,
                "actual_value": result.answer_value,
                "passed": bool(
                    value_match[-1] and response_state.evidence_decision == "SUFFICIENT"
                ),
                "normalized_answer_match": bool(value_match[-1]),
                "token_f1": f1[-1],
                "evidence_support": result.support_status,
                "citation_validity": citation_valid[-1],
                "abstained": result.abstained,
                "retrieval_diagnosis": result.retrieval_diagnosis,
                "primary_state": response_state.primary_state.value,
                "conflict_status": response_state.conflict.category.value,
                "response_state": response_state.model_dump(mode="json"),
                "generation_provider": result.generation_provider,
                "generation_used": result.generation_used,
                "generation_fallback_used": result.generation_fallback_used,
                "generation_verification": result.generation_verification,
            }
        )
    run.metrics_json = {
        "cases": len(cases),
        "exact_match": sum(exact) / len(exact),
        "normalized_answer_match": sum(value_match) / len(value_match),
        "token_f1": sum(f1) / len(f1),
        "answer_rate": answered / len(cases),
        "citation_validity": sum(citation_valid) / len(citation_valid),
        "evidence_support": sum(evidence_supported) / len(evidence_supported),
        "pass_rate": sum(item["passed"] for item in case_results) / len(case_results),
    }
    run.config_json = {**(run.config_json or {}), "case_results": case_results}
    run.status = "completed"
    await session.commit()
    await session.refresh(run)
    return run


def _normalize_value(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\b(the|a|an)\b", " ", value)
    value = re.sub(r"\b(demo topic is|topic is|is|are|was|were)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _value_matches(expected: str, actual: str) -> bool:
    if not expected or not actual:
        return False
    expected_tokens = expected.split()
    actual_tokens = actual.split()
    return (
        expected == actual
        or expected in actual_tokens
        or expected in actual
        or set(expected_tokens) == set(actual_tokens)
    )
