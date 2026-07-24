import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode
from app.llm.base import GenerationRequest
from app.llm.gateway import get_llm_gateway
from app.models.schemas import EvidenceItem, SearchResponse
from app.observability.metrics import (
    ABSTENTIONS,
    DIAGNOSIS_LATENCY,
    KNOWLEDGE_ABSENCE,
    PARTIAL_EVIDENCE,
    RETRIEVAL_LATENCY,
    RETRIEVAL_RECOVERIES,
    RETRIEVAL_RETRIES,
)
from app.rag.abstention import abstention_message
from app.rag.evidence import (
    SupportStatus,
    assess_evidence_support,
    evidence_is_sufficient,
    synthesize_direct_answer,
)
from app.rag.evidence_diagnosis import (
    DiagnosisStatus,
    diagnose_evidence,
    merge_evidence,
    reformulate_query,
)
from app.rag.hybrid_retriever import retrieve
from app.rag.query_rewrite import rewrite_query
from app.security.prompt_security import scan_prompt


async def search_and_answer(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    top_k: int | None = None,
    document_ids: list[UUID] | None = None,
    request_id: str | None = None,
) -> SearchResponse:
    scan = scan_prompt(query)
    if not scan.safe:
        raise AppError(
            ErrorCode.UNSAFE_INPUT,
            "The query contains instructions that conflict with platform security controls",
            400,
        )
    rewritten = rewrite_query(query)
    retrieval_started = time.perf_counter()
    evidence = await retrieve(
        session, workspace_id=workspace_id, query=rewritten, top_k=top_k, document_ids=document_ids
    )
    RETRIEVAL_LATENCY.observe(time.perf_counter() - retrieval_started)
    sufficient = evidence_is_sufficient(
        [e.score for e in evidence], query, [e.content for e in evidence]
    )
    final_evidence = evidence
    final_sufficient = sufficient
    retry_performed = False
    retry_strategy: list[str] = []
    if not sufficient:
        retry_performed = True
        retry_strategy = ["query_reformulation", "top_k_expansion"]
        RETRIEVAL_RETRIES.inc()
        retry_query = reformulate_query(rewritten)
        expanded_top_k = min(max(top_k or 0, 12), 50)
        retrieval_started = time.perf_counter()
        retry_evidence = await retrieve(
            session,
            workspace_id=workspace_id,
            query=retry_query,
            top_k=expanded_top_k,
            document_ids=document_ids,
        )
        RETRIEVAL_LATENCY.observe(time.perf_counter() - retrieval_started)
        final_evidence = merge_evidence(evidence, retry_evidence)
        final_sufficient = evidence_is_sufficient(
            [e.score for e in final_evidence], query, [e.content for e in final_evidence]
        )
    diagnosis_started = time.perf_counter()
    support = assess_evidence_support(
        [e.score for e in final_evidence], query, [e.content for e in final_evidence]
    )
    diagnosis = diagnose_evidence(
        query=query,
        initial_evidence=evidence,
        final_evidence=final_evidence,
        initial_evidence_sufficient=sufficient,
        final_evidence_sufficient=final_sufficient,
        retry_performed=retry_performed,
        retry_strategy=retry_strategy,
    )
    DIAGNOSIS_LATENCY.observe(time.perf_counter() - diagnosis_started)
    if diagnosis.status is DiagnosisStatus.RETRIEVAL_FAILURE_RECOVERED:
        RETRIEVAL_RECOVERIES.inc()
    elif diagnosis.status is DiagnosisStatus.KNOWLEDGE_ABSENT:
        KNOWLEDGE_ABSENCE.inc()
    elif diagnosis.status is DiagnosisStatus.PARTIAL_EVIDENCE:
        PARTIAL_EVIDENCE.inc()

    should_abstain = not final_sufficient or diagnosis.status in {
        DiagnosisStatus.AMBIGUOUS_QUERY,
        DiagnosisStatus.CONFLICTING_EVIDENCE,
        DiagnosisStatus.KNOWLEDGE_ABSENT,
        DiagnosisStatus.PARTIAL_EVIDENCE,
        DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED,
    }
    if support.status is SupportStatus.SUPPORTED:
        should_abstain = False
    if support.status is SupportStatus.CONFLICT:
        should_abstain = True
    if should_abstain:
        ABSTENTIONS.inc()
        return SearchResponse(
            answer=abstention_message(query),
            evidence=[
                EvidenceItem(
                    chunk_id=e.chunk_id,
                    document_id=e.document_id,
                    document_title=e.document_title,
                    content=e.content,
                    score=e.score,
                    metadata=e.metadata,
                )
                for e in final_evidence
            ],
            sufficient_evidence=final_sufficient,
            abstained=True,
            request_id=request_id,
            retrieval_diagnosis=diagnosis.as_dict(),
            outcome=(
                "CONFLICTING_EVIDENCE"
                if support.status is SupportStatus.CONFLICT
                else _outcome_from_diagnosis(diagnosis.status.value)
            ),
            answer_value=support.answer_value,
            support_status=support.status.value,
            confidence_category="none",
            citations=[],
            conflicts=_conflicts_from_support(support),
            abstention_reason=diagnosis.reason_code.value,
        )
    direct_answer = synthesize_direct_answer(query, support)
    if direct_answer:
        answer = direct_answer
    else:
        result = await get_llm_gateway().answer(
            GenerationRequest(question=query, evidence=final_evidence)
        )
        answer = result.text
    return SearchResponse(
        answer=answer,
        evidence=[
            EvidenceItem(
                chunk_id=e.chunk_id,
                document_id=e.document_id,
                document_title=e.document_title,
                content=e.content,
                score=e.score,
                metadata=e.metadata,
            )
            for e in final_evidence
        ],
        sufficient_evidence=True,
        abstained=False,
        request_id=request_id,
        retrieval_diagnosis=diagnosis.as_dict(),
        outcome="ANSWER_SUPPORTED",
        answer_value=support.answer_value,
        support_status=support.status.value,
        confidence_category="high" if support.answer_value else "medium",
        citations=_citations(final_evidence),
        conflicts=[],
        abstention_reason=None,
    )


def _citations(evidence: list) -> list[dict]:
    return [
        {
            "index": index,
            "chunk_id": str(item.chunk_id),
            "document_id": str(item.document_id),
            "document_title": item.document_title,
            "excerpt": item.content[:500],
            "section": (item.metadata or {}).get("section"),
        }
        for index, item in enumerate(evidence[:5], 1)
    ]


def _conflicts_from_support(support) -> list[dict]:
    if support.status is not SupportStatus.CONFLICT:
        return []
    return [
        {
            "status": "CONFIRMED_CONFLICT",
            "attribute": support.attribute.value,
            "values": support.conflict_values,
            "summary": f"Conflicting values found for {support.attribute.value}.",
        }
    ]


def _outcome_from_diagnosis(status: str) -> str:
    return {
        "KNOWLEDGE_ABSENT": "KNOWLEDGE_ABSENT",
        "AMBIGUOUS_QUERY": "CLARIFICATION_REQUIRED",
        "CONFLICTING_EVIDENCE": "CONFLICTING_EVIDENCE",
        "PARTIAL_EVIDENCE": "ANSWER_PARTIALLY_SUPPORTED",
        "RETRIEVAL_FAILURE_UNRESOLVED": "INSUFFICIENT_EVIDENCE",
        "RETRIEVAL_FAILURE_RECOVERED": "ANSWER_SUPPORTED",
        "SUFFICIENT_EVIDENCE": "ANSWER_SUPPORTED",
    }.get(status, "INSUFFICIENT_EVIDENCE")
