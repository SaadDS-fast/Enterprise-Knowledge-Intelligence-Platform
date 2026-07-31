import re
import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document
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
)
from app.rag.evidence_diagnosis import (
    DiagnosisStatus,
    diagnose_evidence,
    merge_evidence,
    reformulate_query,
)
from app.rag.evidence_sufficiency import assess_sufficiency
from app.rag.hybrid_retriever import retrieve
from app.rag.query_intent import classify_query_intent
from app.rag.query_rewrite import rewrite_query
from app.rag.topic_lists import (
    discover_topic_items,
    has_practice_questions,
    is_topic_list_query,
    synthesize_topic_list,
    topic_list_abstention_message,
)
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
    active_scope = await _resolve_document_scope(session, workspace_id, query, document_ids)
    query_intent = classify_query_intent(query)
    effective_document_ids = [item["document_id"] for item in active_scope] or document_ids
    rewritten = rewrite_query(query)
    retrieval_started = time.perf_counter()
    evidence = await retrieve(
        session,
        workspace_id=workspace_id,
        query=rewritten,
        top_k=top_k,
        document_ids=effective_document_ids,
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
            document_ids=effective_document_ids,
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
    diagnosis_payload = {
        **diagnosis.as_dict(),
        **_retrieval_metadata(final_evidence),
        "retrieval_recovery_used": retry_performed,
    }
    sufficiency = assess_sufficiency(
        intent=query_intent,
        support=support,
        candidate_count=len(final_evidence),
        retry_performed=retry_performed,
        low_quality=bool(final_evidence)
        and all(
            item.metadata.get("extraction_quality") == "low_quality" for item in final_evidence
        ),
    )
    diagnosis_payload.update(
        {
            "query_intent": query_intent.value,
            "sufficiency_decision": sufficiency.decision.value,
            "sufficiency_reason": sufficiency.reason,
        }
    )

    if is_topic_list_query(query):
        topic_items = discover_topic_items(final_evidence)
        evidence_items = _evidence_items(final_evidence)
        if topic_items:
            topic_citations = _topic_citations(topic_items)
            return SearchResponse(
                answer=synthesize_topic_list(topic_items),
                evidence=evidence_items,
                sufficient_evidence=True,
                abstained=False,
                request_id=request_id,
                retrieval_diagnosis={
                    **diagnosis_payload,
                    "status": DiagnosisStatus.SUFFICIENT_EVIDENCE.value,
                    "reason_code": "TOPIC_LIST_SUPPORTED",
                },
                outcome="ANSWER_SUPPORTED",
                answer_value=", ".join(item.label for item in topic_items),
                support_status=SupportStatus.SUPPORTED.value,
                confidence_category="high",
                citations=topic_citations,
                conflicts=[],
                abstention_reason=None,
                topic_items=[item.as_dict() for item in topic_items],
                active_document_scope=_scope_payload(active_scope),
            )
        ABSTENTIONS.inc()
        status = (
            DiagnosisStatus.PARTIAL_EVIDENCE.value
            if has_practice_questions(final_evidence)
            else diagnosis.status.value
        )
        return SearchResponse(
            answer=topic_list_abstention_message(),
            evidence=evidence_items,
            sufficient_evidence=False,
            abstained=True,
            request_id=request_id,
            retrieval_diagnosis={
                **diagnosis_payload,
                "status": status,
                "reason_code": "LOW_CONFIDENCE_TOPIC_INFERENCE",
            },
            outcome="INSUFFICIENT_EVIDENCE",
            answer_value=None,
            support_status=SupportStatus.ABSENT.value,
            confidence_category="none",
            citations=[],
            conflicts=[],
            abstention_reason="LOW_CONFIDENCE_TOPIC_INFERENCE",
            topic_items=[],
            active_document_scope=_scope_payload(active_scope),
        )

    should_abstain = not final_sufficient or diagnosis.status in {
        DiagnosisStatus.AMBIGUOUS_QUERY,
        DiagnosisStatus.CONFLICTING_EVIDENCE,
        DiagnosisStatus.KNOWLEDGE_ABSENT,
        DiagnosisStatus.PARTIAL_EVIDENCE,
        DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED,
    }
    if support.status is SupportStatus.SUPPORTED:
        should_abstain = not sufficiency.sufficient
    if support.status is SupportStatus.CONFLICT:
        should_abstain = True
    if should_abstain:
        ABSTENTIONS.inc()
        return SearchResponse(
            answer=abstention_message(query),
            evidence=_evidence_items(final_evidence),
            sufficient_evidence=final_sufficient,
            abstained=True,
            request_id=request_id,
            retrieval_diagnosis=diagnosis_payload,
            outcome=(
                "CONFLICTING_EVIDENCE"
                if support.status is SupportStatus.CONFLICT
                else _outcome_from_diagnosis(diagnosis.status.value)
            ),
            answer_value=support.answer_value,
            support_status=support.status.value,
            confidence_category="none",
            citations=_citations(final_evidence, support)
            if support.status is SupportStatus.CONFLICT
            else [],
            conflicts=_conflicts_from_support(support),
            abstention_reason=diagnosis.reason_code.value,
            active_document_scope=_scope_payload(active_scope),
        )
    result = await get_llm_gateway().answer(
        GenerationRequest(question=query, evidence=final_evidence)
    )
    answer = result.text
    citations = list(result.citations) if result.used else _citations(final_evidence, support)
    return SearchResponse(
        answer=answer,
        evidence=_evidence_items(final_evidence),
        sufficient_evidence=True,
        abstained=False,
        request_id=request_id,
        retrieval_diagnosis=diagnosis_payload,
        outcome="ANSWER_SUPPORTED",
        answer_value=support.answer_value,
        support_status=support.status.value,
        confidence_category="high" if support.answer_value else "medium",
        citations=citations,
        conflicts=[],
        abstention_reason=None,
        active_document_scope=_scope_payload(active_scope),
        generation_provider=result.provider,
        generation_model=result.model,
        generation_used=result.used,
        generation_fallback_used=result.fallback_used,
        generation_duration_ms=result.duration_ms,
        generation_verification=result.verification,
        structured_output_valid=result.structured_output_valid,
        claim_verification_passed=result.claim_verification_passed,
    )


def _evidence_items(evidence: list) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            chunk_id=e.chunk_id,
            document_id=e.document_id,
            document_title=e.document_title,
            content=e.content,
            score=e.score,
            metadata=e.metadata,
        )
        for e in evidence
    ]


def _retrieval_metadata(evidence: list) -> dict:
    if not evidence:
        return {
            "retrieval_mode": "no_candidates",
            "lexical_used": True,
            "semantic_used": False,
            "reranker_used": False,
            "fallback_used": False,
            "candidate_count": 0,
            "final_evidence_count": 0,
            "retrieval_duration_ms": 0.0,
            "embedding_version": None,
            "reranker_version": None,
            "selected_document_scope": False,
        }
    metadata = evidence[0].metadata or {}
    keys = {
        "retrieval_mode",
        "lexical_used",
        "semantic_used",
        "reranker_used",
        "fallback_used",
        "candidate_count",
        "final_evidence_count",
        "retrieval_duration_ms",
        "embedding_version",
        "reranker_version",
        "selected_document_scope",
        "query_intent",
        "reranker_policy",
        "reranker_applied",
        "reranker_skipped",
        "reranker_low_margin_fallback",
        "fused_rank_preserved",
        "blended_reranking_used",
    }
    return {key: metadata.get(key) for key in keys}


def _citations(evidence: list, support=None) -> list[dict]:
    facts = list(support.facts) if support else []
    selected = (
        [
            (fact.source_index, evidence[fact.source_index], fact)
            for fact in facts
            if fact.source_index < len(evidence)
        ]
        if facts
        else [(0, evidence[0], None)]
        if evidence
        else []
    )
    return [
        {
            "index": citation_index,
            "chunk_id": str(item.chunk_id),
            "document_id": str(item.document_id),
            "document_title": item.document_title,
            "excerpt": fact.matched_text if fact else _focused_excerpt(item.content),
            "section": (item.metadata or {}).get("section"),
            "supports_claim": support.answer_value if support else None,
        }
        for citation_index, (_, item, fact) in enumerate(selected, 1)
    ]


def _focused_excerpt(content: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", content)]
    return next((sentence[:500] for sentence in sentences if sentence), "")


def _topic_citations(topic_items: list) -> list[dict]:
    return [
        {
            "index": index,
            "chunk_id": str(item.chunk_id),
            "document_id": str(item.document_id),
            "document_title": item.document_title,
            "excerpt": item.excerpt[:500],
            "section": item.section,
            "topic": item.label,
        }
        for index, item in enumerate(topic_items, 1)
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


async def _resolve_document_scope(
    session: AsyncSession, workspace_id: UUID, query: str, document_ids: list[UUID] | None
) -> list[dict]:
    if document_ids:
        unique_ids = list(dict.fromkeys(document_ids))
        documents = (
            await session.scalars(
                select(Document).where(
                    Document.workspace_id == workspace_id,
                    Document.status == "ready",
                    Document.id.in_(unique_ids),
                )
            )
        ).all()
        if len(documents) != len(unique_ids):
            raise AppError(
                ErrorCode.NOT_FOUND,
                "One or more selected documents were not found in this workspace",
                404,
            )
        return [{"document_id": document.id, "title": document.title} for document in documents]
    named = await _infer_named_document_scope(session, workspace_id, query)
    return [{"document_id": document.id, "title": document.title} for document in named]


async def _infer_named_document_scope(
    session: AsyncSession, workspace_id: UUID, query: str
) -> list[Document]:
    normalized_query = _scope_key(query)
    documents = (
        await session.scalars(
            select(Document).where(
                Document.workspace_id == workspace_id, Document.status == "ready"
            )
        )
    ).all()
    matches = [document for document in documents if _scope_key(document.title) in normalized_query]
    if len(matches) == 1:
        return matches
    title_terms = set(normalized_query.split())
    fuzzy = [
        document
        for document in documents
        if len(set(_scope_key(document.title).split()) & title_terms) >= 2
    ]
    return fuzzy if len(fuzzy) == 1 else []


def _scope_key(value: str) -> str:
    return re.sub(r"\W+", " ", value).strip().lower()


def _scope_payload(scope: list[dict]) -> list[dict]:
    return [{"document_id": str(item["document_id"]), "title": item["title"]} for item in scope]
