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
from app.rag.evidence import evidence_is_sufficient
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
        )
    result = await get_llm_gateway().answer(
        GenerationRequest(question=query, evidence=final_evidence)
    )
    return SearchResponse(
        answer=result.text,
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
    )
