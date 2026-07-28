from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Chunk, Document, DocumentVersion
from app.models.domain import RetrievedEvidence
from app.rag.bm25 import bm25_scores
from app.rag.embeddings import cosine_similarity
from app.rag.evidence import ATTRIBUTE_LABELS, requested_attribute
from app.rag.fusion import weighted_fusion
from app.rag.query_intent import classify_query_intent
from app.rag.reranker_provider import rerank
from app.rag.semantic_provider import embed_with_fallback


@dataclass(frozen=True, slots=True)
class Candidate:
    chunk: Chunk
    version: DocumentVersion
    document: Document
    lexical: float
    semantic: float
    semantic_compatible: bool
    lexical_rank: int
    semantic_rank: int
    fused: float
    title_heading_boost: float
    quality_factor: float


async def retrieve(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    query: str,
    top_k: int | None = None,
    document_ids: list[UUID] | None = None,
) -> list[RetrievedEvidence]:
    started = time.perf_counter()
    normalized_query = _normalize_query(query)
    intent = classify_query_intent(normalized_query)
    latest_version = (
        select(func.max(DocumentVersion.version_number))
        .where(DocumentVersion.document_id == Document.id)
        .correlate(Document)
        .scalar_subquery()
    )
    statement = (
        select(Chunk, DocumentVersion, Document)
        .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(
            Chunk.workspace_id == workspace_id,
            Document.workspace_id == workspace_id,
            Document.status.in_(("ready", "ready_with_warnings")),
            DocumentVersion.version_number == latest_version,
        )
    )
    if document_ids:
        statement = statement.where(Document.id.in_(document_ids))
    rows = (await session.execute(statement)).all()
    if not rows:
        return []

    contents = [row.Chunk.content for row in rows]
    lexical = bm25_scores(normalized_query, contents)
    query_vectors, provider, embedding_fallback = await embed_with_fallback([normalized_query])
    query_vector = query_vectors[0]
    semantic: list[float] = []
    compatible: list[bool] = []
    for row in rows:
        metadata = row.Chunk.metadata_json or {}
        vector = list(row.Chunk.embedding or [])
        is_compatible = (
            len(vector) == provider.identity.dimension
            and metadata.get("embedding_version") == provider.identity.version
            and metadata.get("embedding_dimension") == provider.identity.dimension
        )
        compatible.append(is_compatible)
        semantic.append(cosine_similarity(query_vector, vector) if is_compatible else -1.0)
    semantic_active = any(compatible) and not embedding_fallback
    fusion_active = semantic_active or (
        any(compatible) and not settings.semantic_embeddings_enabled
    )
    fused = (
        weighted_fusion(
            lexical,
            semantic,
            lexical_weight=settings.hybrid_lexical_weight,
            semantic_weight=settings.hybrid_semantic_weight,
        )
        if fusion_active
        else lexical.copy()
    )
    lexical_ranks = _ranks(lexical)
    semantic_ranks = _ranks(semantic)
    candidates: list[Candidate] = []
    for index, row in enumerate(rows):
        metadata = row.Chunk.metadata_json or {}
        boost = _title_heading_boost(
            normalized_query,
            row.Document.title,
            str(metadata.get("heading") or metadata.get("section") or ""),
            row.Chunk.content,
        )
        quality_factor = _quality_factor(metadata)
        calibrated = max(0.0, min(1.0, (fused[index] + boost) * quality_factor))
        candidates.append(
            Candidate(
                row.Chunk,
                row.DocumentVersion,
                row.Document,
                lexical[index],
                semantic[index],
                compatible[index],
                lexical_ranks[index],
                semantic_ranks[index],
                calibrated,
                boost,
                quality_factor,
            )
        )
    candidates.sort(key=lambda item: item.fused, reverse=True)
    candidates = _deduplicate(candidates)[: settings.reranker_top_n]
    reranked = await rerank(
        normalized_query,
        [item.chunk.content for item in candidates],
        [item.fused for item in candidates],
        intent,
    )
    scored = list(zip(candidates, reranked.scores, strict=True))
    scored.sort(key=lambda item: item[1], reverse=True)
    return_k = min(
        top_k or settings.reranker_return_k,
        settings.retrieval_top_k,
        len(scored),
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    retrieval_mode = (
        "hybrid_lexical_semantic" if semantic_active else "lexical_with_deterministic_fallback"
    )
    result: list[RetrievedEvidence] = []
    for final_rank, (candidate, final_score) in enumerate(scored[:return_k], 1):
        metadata = candidate.chunk.metadata_json or {}
        result.append(
            RetrievedEvidence(
                chunk_id=candidate.chunk.id,
                document_id=candidate.document.id,
                document_title=candidate.document.title,
                content=candidate.chunk.content,
                score=max(0.0, min(1.0, final_score)),
                metadata={
                    **metadata,
                    "retrieval_stage": "hybrid_bm25_semantic_rerank",
                    "retrieval_mode": retrieval_mode,
                    "lexical_used": True,
                    "semantic_used": semantic_active,
                    "reranker_used": reranked.used,
                    "fallback_used": embedding_fallback or reranked.fallback_used,
                    "candidate_count": len(rows),
                    "final_evidence_count": return_k,
                    "retrieval_duration_ms": duration_ms,
                    "embedding_version": provider.identity.version,
                    "reranker_version": reranked.version,
                    "query_intent": intent.value,
                    "reranker_policy": reranked.policy,
                    "reranker_applied": reranked.used,
                    "reranker_skipped": not reranked.used and not reranked.fallback_used,
                    "reranker_low_margin_fallback": reranked.policy == "low_margin_fused",
                    "fused_rank_preserved": reranked.policy
                    in {"low_margin_fused", "intent_skipped", "unavailable_fused"},
                    "blended_reranking_used": reranked.policy == "blended",
                    "lexical_rank": candidate.lexical_rank,
                    "lexical_score": round(candidate.lexical, 6),
                    "semantic_rank": candidate.semantic_rank
                    if candidate.semantic_compatible
                    else None,
                    "semantic_score": round(candidate.semantic, 6)
                    if candidate.semantic > -1
                    else None,
                    "fused_score": round(candidate.fused, 6),
                    "title_heading_boost": round(candidate.title_heading_boost, 6),
                    "quality_factor": candidate.quality_factor,
                    "selected_document_scope": bool(document_ids),
                    "final_rank": final_rank,
                    "requires_reindex": metadata.get("embedding_version")
                    != provider.identity.version,
                },
            )
        )
    return result


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().split())


def _ranks(scores: list[float]) -> list[int]:
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    ranks = [0] * len(scores)
    for rank, index in enumerate(order, 1):
        ranks[index] = rank
    return ranks


def _title_heading_boost(query: str, title: str, heading: str, content: str) -> float:
    attribute = requested_attribute(query)
    boost = 0.0
    if _contains_phrase(query, title):
        boost += 0.04
    if heading and _contains_phrase(query, heading):
        boost += 0.08
    labels = ATTRIBUTE_LABELS.get(attribute, ())
    if labels and any(f"{label}:" in content.lower() for label in labels):
        boost += 0.12
    # A title alone must never overcome absent content support.
    if boost and not _contains_phrase(query, content):
        boost *= 0.5
    return boost


def _quality_factor(metadata: dict) -> float:
    quality = metadata.get("extraction_quality")
    if isinstance(quality, dict):
        quality = quality.get("status")
    return {
        "high_quality": 1.0,
        "acceptable": 0.92,
        "low_quality": 0.72,
    }.get(str(quality or "").lower(), 0.85)


def _deduplicate(candidates: list[Candidate]) -> list[Candidate]:
    result: list[Candidate] = []
    seen: set[tuple[UUID, str]] = set()
    for candidate in candidates:
        key = (candidate.document.id, " ".join(candidate.chunk.content.lower().split())[:240])
        if key not in seen:
            result.append(candidate)
            seen.add(key)
    return result


def _contains_phrase(query: str, value: str) -> bool:
    query_terms = {term for term in query.lower().split() if len(term) >= 4}
    normalized = value.lower()
    return any(term in normalized for term in query_terms)
