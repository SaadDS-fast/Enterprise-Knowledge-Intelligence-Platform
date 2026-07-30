from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from math import isclose
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator, model_validator

from app.agents.schemas import ExternalSource
from app.core.config import settings
from app.models.domain import RetrievedEvidence
from app.models.schemas import EvidenceItem
from app.observability.metrics import (
    AGENT_CITATIONS_REJECTED,
    AGENT_CITATIONS_VALIDATED,
    AGENT_CLAIMS_UNSUPPORTED,
    AGENT_CLAIMS_VERIFIED,
    AGENT_CONFLICTS_DETECTED,
    AGENT_CONTEXT_BUDGET_TRUNCATIONS,
    AGENT_EVIDENCE_DEDUPLICATED,
    AGENT_EVIDENCE_ITEMS,
)
from app.rag.evidence import (
    SupportStatus,
    assess_evidence_support,
    key_terms,
    synthesize_direct_answer,
)
from app.rag.evidence_diagnosis import DiagnosisStatus
from app.rag.response_state import (
    ConflictCategory,
    classify_claim_conflict,
    normalize_claim,
)
from app.rag.topic_lists import (
    discover_topic_items,
    has_practice_questions,
    is_topic_list_query,
    synthesize_topic_list,
    topic_list_abstention_message,
)


class EvidenceSourceType(StrEnum):
    INTERNAL_DOCUMENT = "internal_document"
    WEB_SEARCH = "web_search"
    WIKIPEDIA = "wikipedia"
    ARXIV = "arxiv"
    APPROVED_API = "approved_api"


class VerificationStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTED = "CONFLICTED"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"


class ConflictStatus(StrEnum):
    NO_CONFLICT = "NO_CONFLICT"
    POSSIBLE_CONFLICT = "POSSIBLE_CONFLICT"
    CONFIRMED_CONFLICT = "CONFIRMED_CONFLICT"


class AnswerOutcome(StrEnum):
    ANSWER_SUPPORTED = "ANSWER_SUPPORTED"
    ANSWER_PARTIALLY_SUPPORTED = "ANSWER_PARTIALLY_SUPPORTED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    KNOWLEDGE_ABSENT = "KNOWLEDGE_ABSENT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    FAILED = "FAILED"


class ConfidenceCategory(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class UnifiedEvidence(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=160)
    source_type: EvidenceSourceType
    provider: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    excerpt: str = Field(min_length=1, max_length=2000)
    canonical_url: str | None = Field(default=None, max_length=2000)
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    chunk_id: UUID | None = None
    page_number: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, max_length=200)
    retrieval_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reranker_score: float | None = Field(default=None, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    combined_score: float = Field(default=0.0, ge=0.0, le=2.0)
    retrieval_timestamp: datetime
    publication_date: str | None = Field(default=None, max_length=80)
    authors: list[str] = Field(default_factory=list, max_length=20)
    tenant_id: UUID | None = None
    workspace_id: UUID | None = None
    citation_label: str = Field(min_length=2, max_length=24)
    untrusted_external_content: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    merged_source_ids: list[str] = Field(default_factory=list)
    duplicate_count: int = 0

    @field_validator("canonical_url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        if value is not None:
            HttpUrl(value)
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> UnifiedEvidence:
        if self.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
            if self.document_id is None or self.chunk_id is None:
                raise ValueError("Internal evidence requires document_id and chunk_id")
            if self.workspace_id is None or self.tenant_id is None:
                raise ValueError("Internal evidence requires tenant and workspace scope")
            if self.untrusted_external_content:
                raise ValueError("Internal evidence cannot be marked as external content")
        else:
            if not self.canonical_url:
                raise ValueError("External evidence requires canonical_url")
            if self.tenant_id is not None or self.workspace_id is not None:
                raise ValueError("External evidence cannot carry tenant or workspace scope")
            if not self.untrusted_external_content:
                raise ValueError("External evidence must remain untrusted")
        return self


class DeduplicationRecord(BaseModel):
    duplicate_count: int
    merged_source_ids: list[str]
    retained_evidence_id: str


class EvidenceAggregationResult(BaseModel):
    evidence: list[UnifiedEvidence]
    deduplication: list[DeduplicationRecord] = Field(default_factory=list)
    ranking: dict[str, Any] = Field(default_factory=dict)
    context_budget: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    claim_id: str = Field(min_length=1, max_length=80)
    claim_text: str = Field(min_length=1, max_length=1000)
    claim_type: str = Field(default="factual", max_length=80)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    support_score: float = Field(default=0.0, ge=0.0, le=1.0)
    verification_status: VerificationStatus


class Conflict(BaseModel):
    status: ConflictStatus
    conflict_type: str = Field(default="unknown", max_length=80)
    evidence_ids: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1000)


class CitationValidationResult(BaseModel):
    citations: list[dict[str, Any]]
    rejected: list[dict[str, Any]] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    answer: str
    claims: list[Claim]
    citations: list[dict[str, Any]]
    unsupported_claims_removed: list[str] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    abstained: bool = False
    confidence_category: ConfidenceCategory = ConfidenceCategory.NONE
    outcome: AnswerOutcome = AnswerOutcome.INSUFFICIENT_EVIDENCE


def normalize_internal_evidence(
    items: list[EvidenceItem], *, tenant_id: UUID, workspace_id: UUID
) -> list[UnifiedEvidence]:
    normalized: list[UnifiedEvidence] = []
    for index, item in enumerate(items, 1):
        metadata = dict(item.metadata or {})
        try:
            normalized.append(
                UnifiedEvidence(
                    evidence_id=f"int:{item.document_id}:{item.chunk_id}",
                    source_type=EvidenceSourceType.INTERNAL_DOCUMENT,
                    provider="internal",
                    title=item.document_title,
                    excerpt=_compact_text(item.content),
                    document_id=item.document_id,
                    document_version_id=_uuid_or_none(metadata.get("document_version_id")),
                    chunk_id=item.chunk_id,
                    page_number=_int_or_none(metadata.get("page_number")),
                    section=_str_or_none(metadata.get("section")),
                    retrieval_score=item.score,
                    reranker_score=item.score,
                    trust_score=1.0,
                    freshness_score=0.5,
                    combined_score=item.score,
                    retrieval_timestamp=datetime.now(UTC),
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    citation_label=f"D{index}",
                    untrusted_external_content=False,
                    metadata=metadata,
                )
            )
        except ValidationError as exc:
            raise ValueError("malformed_internal_evidence") from exc
    AGENT_EVIDENCE_ITEMS.labels(source_type=EvidenceSourceType.INTERNAL_DOCUMENT.value).inc(
        len(normalized)
    )
    return normalized


def normalize_external_sources(items: list[ExternalSource]) -> list[UnifiedEvidence]:
    normalized: list[UnifiedEvidence] = []
    for index, item in enumerate(items, 1):
        source_type = _external_source_type(item)
        try:
            normalized.append(
                UnifiedEvidence(
                    evidence_id=f"ext:{item.provider}:{_stable_digest(item.source_id)}",
                    source_type=source_type,
                    provider=item.provider,
                    title=item.title,
                    excerpt=_compact_text(item.excerpt),
                    canonical_url=item.canonical_url,
                    retrieval_score=_rank_score(item.rank),
                    reranker_score=None,
                    trust_score=_trust_score(source_type, item.provider),
                    freshness_score=_freshness_score(item.publication_date),
                    combined_score=0.0,
                    retrieval_timestamp=item.retrieval_timestamp,
                    publication_date=item.publication_date,
                    authors=item.authors,
                    citation_label=f"E{index}",
                    untrusted_external_content=True,
                    metadata={
                        "source_id": item.source_id,
                        "trust_category": item.trust_category,
                        "rank": item.rank,
                    },
                )
            )
        except ValidationError as exc:
            raise ValueError("malformed_external_evidence") from exc
    for source_type, count in _counts_by_source(normalized).items():
        AGENT_EVIDENCE_ITEMS.labels(source_type=source_type).inc(count)
    return normalized


def normalize_approved_api_sources(items: list[ExternalSource]) -> list[UnifiedEvidence]:
    normalized = normalize_external_sources(items)
    return [
        item.model_copy(update={"source_type": EvidenceSourceType.APPROVED_API})
        if item.source_type == EvidenceSourceType.WEB_SEARCH
        else item
        for item in normalized
    ]


def aggregate_evidence(query: str, evidence: list[UnifiedEvidence]) -> EvidenceAggregationResult:
    deduped, records = deduplicate_evidence(evidence)
    ranked = rank_evidence(query, deduped)
    budgeted, budget_metadata = apply_context_budget(ranked)
    return EvidenceAggregationResult(
        evidence=budgeted,
        deduplication=records,
        ranking={
            "method": "reciprocal_rank_fusion",
            "rrf_k": settings.evidence_rrf_k,
            "internal_priority_weight": settings.evidence_internal_priority_weight,
            "external_trust_weight": settings.evidence_external_trust_weight,
        },
        context_budget=budget_metadata,
    )


def deduplicate_evidence(
    evidence: list[UnifiedEvidence],
) -> tuple[list[UnifiedEvidence], list[DeduplicationRecord]]:
    retained: list[UnifiedEvidence] = []
    records: list[DeduplicationRecord] = []
    buckets: dict[str, UnifiedEvidence] = {}
    for item in evidence:
        key = _dedupe_key(item)
        existing = buckets.get(key)
        if existing is None:
            buckets[key] = item
            retained.append(item)
            continue
        if not _can_merge(existing, item):
            retained.append(item)
            continue
        merged_ids = sorted({*existing.merged_source_ids, existing.evidence_id, item.evidence_id})
        duplicate_count = existing.duplicate_count + 1
        updated = existing.model_copy(
            update={
                "merged_source_ids": merged_ids,
                "duplicate_count": duplicate_count,
                "combined_score": max(existing.combined_score, item.combined_score),
            }
        )
        buckets[key] = updated
        retained[retained.index(existing)] = updated
        records.append(
            DeduplicationRecord(
                duplicate_count=duplicate_count,
                merged_source_ids=merged_ids,
                retained_evidence_id=updated.evidence_id,
            )
        )
        AGENT_EVIDENCE_DEDUPLICATED.labels(source_type=item.source_type.value).inc()
    return retained, records


def rank_evidence(query: str, evidence: list[UnifiedEvidence]) -> list[UnifiedEvidence]:
    time_sensitive = _is_time_sensitive(query)
    ranked: list[UnifiedEvidence] = []
    for index, item in enumerate(evidence, 1):
        retrieval = item.retrieval_score or 0.0
        rrf = 1.0 / (settings.evidence_rrf_k + index)
        source_weight = (
            settings.evidence_internal_priority_weight
            if item.source_type == EvidenceSourceType.INTERNAL_DOCUMENT
            else settings.evidence_external_trust_weight
        )
        freshness = item.freshness_score if time_sensitive else 0.5
        query_overlap = _term_overlap(query, item.excerpt)
        duplicate_penalty = min(0.15, item.duplicate_count * 0.03)
        combined = (
            (retrieval * 0.45)
            + (item.trust_score * 0.2 * source_weight)
            + (query_overlap * 0.2)
            + (freshness * 0.1)
            + (rrf * 3)
            - duplicate_penalty
        )
        ranked.append(item.model_copy(update={"combined_score": round(max(0.0, combined), 6)}))
    ranked.sort(key=lambda item: (-item.combined_score, item.citation_label, item.evidence_id))
    return _renumber_citations(ranked)


def apply_context_budget(
    evidence: list[UnifiedEvidence],
) -> tuple[list[UnifiedEvidence], dict[str, Any]]:
    max_items = settings.evidence_max_items
    max_chars = settings.evidence_context_max_chars
    selected: list[UnifiedEvidence] = []
    source_counts: dict[str, int] = defaultdict(int)
    used_fingerprints: set[str] = set()
    chars = 0
    for item in evidence:
        source_type = item.source_type.value
        if source_type == EvidenceSourceType.INTERNAL_DOCUMENT.value:
            if source_counts[source_type] >= settings.evidence_max_internal_items:
                continue
        elif source_counts[source_type] >= settings.evidence_max_external_items:
            continue
        fingerprint = _content_fingerprint(item.excerpt)
        repeated_external = (
            item.source_type != EvidenceSourceType.INTERNAL_DOCUMENT
            and fingerprint in used_fingerprints
        )
        if repeated_external:
            continue
        projected = chars + len(item.excerpt)
        if len(selected) >= max_items or projected > max_chars:
            continue
        selected.append(item)
        used_fingerprints.add(fingerprint)
        source_counts[source_type] += 1
        chars = projected
    if len(selected) < len(evidence):
        AGENT_CONTEXT_BUDGET_TRUNCATIONS.labels(outcome="truncated").inc()
    return _renumber_citations(selected), {
        "max_items": max_items,
        "max_chars": max_chars,
        "input_count": len(evidence),
        "retained_count": len(selected),
        "truncated_count": max(0, len(evidence) - len(selected)),
        "source_counts": dict(source_counts),
    }


def verify_claims(
    query: str, evidence: list[UnifiedEvidence]
) -> tuple[list[Claim], list[Conflict]]:
    conflicts = detect_conflicts(evidence, query=query)
    conflict_ids = {evidence_id for conflict in conflicts for evidence_id in conflict.evidence_ids}
    claims: list[Claim] = []
    for index, item in enumerate(evidence[: settings.evidence_max_items], 1):
        assessment = assess_evidence_support([item.retrieval_score or 0.0], query, [item.excerpt])
        claim_text = synthesize_direct_answer(query, assessment) or _extract_claim_text(
            item.excerpt
        )
        support_score = _support_score(query, claim_text, item)
        if assessment.status is SupportStatus.SUPPORTED:
            support_score = max(support_score, assessment.support_score)
        if item.evidence_id in conflict_ids:
            status = VerificationStatus.CONFLICTED
        elif support_score >= settings.evidence_min_support_score:
            status = VerificationStatus.SUPPORTED
        elif support_score >= max(0.35, settings.evidence_min_support_score - 0.25):
            status = VerificationStatus.PARTIALLY_SUPPORTED
        else:
            status = VerificationStatus.UNSUPPORTED
        claim = Claim(
            claim_id=f"C{index}",
            claim_text=claim_text,
            supporting_evidence_ids=[item.evidence_id]
            if status in {VerificationStatus.SUPPORTED, VerificationStatus.PARTIALLY_SUPPORTED}
            else [],
            contradicting_evidence_ids=[item.evidence_id]
            if status == VerificationStatus.CONFLICTED
            else [],
            support_score=round(support_score, 4),
            verification_status=status,
        )
        AGENT_CLAIMS_VERIFIED.labels(verification_status=status.value).inc()
        if status == VerificationStatus.UNSUPPORTED:
            AGENT_CLAIMS_UNSUPPORTED.labels(outcome="removed").inc()
        claims.append(claim)
    return claims, conflicts


def detect_conflicts(evidence: list[UnifiedEvidence], *, query: str = "") -> list[Conflict]:
    conflicts: list[Conflict] = []
    for item in evidence:
        if query and not _query_comparable(query, item):
            continue
        status, conflict_type = _self_conflict(item.excerpt)
        if status == ConflictStatus.NO_CONFLICT:
            continue
        conflicts.append(
            Conflict(
                status=status,
                conflict_type=conflict_type,
                evidence_ids=[item.evidence_id],
                summary=(
                    f"{item.citation_label} contains a material "
                    f"{conflict_type.replace('_', ' ')} conflict."
                ),
            )
        )
        AGENT_CONFLICTS_DETECTED.labels(outcome=status.value).inc()
    for left_index, left in enumerate(evidence):
        for right in evidence[left_index + 1 :]:
            if query and (
                not _query_comparable(query, left) or not _query_comparable(query, right)
            ):
                continue
            normalized_left = normalize_claim(
                left.excerpt,
                claim_id=left.evidence_id,
                citation_ids=[left.evidence_id],
                metadata=left.metadata,
            )
            normalized_right = normalize_claim(
                right.excerpt,
                claim_id=right.evidence_id,
                citation_ids=[right.evidence_id],
                metadata=right.metadata,
            )
            result = classify_claim_conflict(normalized_left, normalized_right)
            if (
                result.category == ConflictCategory.NO_CONFLICT
                and normalized_left.attribute is None
                and normalized_right.attribute is None
            ):
                legacy_status, legacy_type = _conflict_between(left.excerpt, right.excerpt)
                if legacy_status != ConflictStatus.NO_CONFLICT:
                    category = {
                        "date": ConflictCategory.DATE_CONFLICT,
                        "numeric_value": ConflictCategory.VALUE_CONFLICT,
                        "owner_entity": ConflictCategory.ROLE_CONFLICT,
                        "opposing_status": ConflictCategory.POLICY_RULE_CONFLICT,
                        "negation": ConflictCategory.POLICY_RULE_CONFLICT,
                    }.get(legacy_type, ConflictCategory.DEFINITION_CONFLICT)
                    result = result.model_copy(
                        update={
                            "category": category,
                            "unresolved": True,
                            "material": True,
                        }
                    )
            if result.category == ConflictCategory.NO_CONFLICT or not result.unresolved:
                continue
            conflict = Conflict(
                status=ConflictStatus.CONFIRMED_CONFLICT,
                conflict_type=result.category.value,
                evidence_ids=[left.evidence_id, right.evidence_id],
                summary=(
                    f"{left.citation_label} and {right.citation_label} contain "
                    f"a material {result.category.value.replace('_', ' ').lower()}."
                ),
            )
            conflicts.append(conflict)
            AGENT_CONFLICTS_DETECTED.labels(outcome=conflict.status.value).inc()
    return conflicts


def deterministic_synthesize(
    query: str, evidence: list[UnifiedEvidence], diagnosis: dict[str, Any]
) -> SynthesisResult:
    if is_topic_list_query(query):
        topic_result = _synthesize_topic_list_answer(query, evidence)
        if topic_result is not None:
            return topic_result
    claims, conflicts = verify_claims(query, evidence)
    supported = [
        claim
        for claim in claims
        if claim.verification_status
        in {VerificationStatus.SUPPORTED, VerificationStatus.PARTIALLY_SUPPORTED}
    ]
    unsupported = [
        claim.claim_text
        for claim in claims
        if claim.verification_status == VerificationStatus.UNSUPPORTED
    ]
    if any(conflict.status == ConflictStatus.CONFIRMED_CONFLICT for conflict in conflicts):
        answer = _conflict_answer(evidence, conflicts)
        validation = validate_citations(
            _citations_for_evidence(evidence, [eid for c in conflicts for eid in c.evidence_ids]),
            evidence,
            claims,
        )
        return SynthesisResult(
            answer=answer,
            claims=claims,
            citations=validation.citations,
            unsupported_claims_removed=unsupported,
            conflicts=conflicts,
            abstained=True,
            confidence_category=ConfidenceCategory.LOW,
            outcome=AnswerOutcome.CONFLICTING_EVIDENCE,
        )
    if supported:
        answer_parts = [
            f"{claim.claim_text} [{_label_for(claim.supporting_evidence_ids[0], evidence)}]"
            for claim in supported[:3]
        ]
        validation = validate_citations(
            _citations_for_evidence(
                evidence, [eid for claim in supported for eid in claim.supporting_evidence_ids]
            ),
            evidence,
            supported,
        )
        has_supported_claim = any(
            claim.verification_status == VerificationStatus.SUPPORTED for claim in supported
        )
        partial = any(
            claim.verification_status == VerificationStatus.PARTIALLY_SUPPORTED
            for claim in supported
        ) or (bool(unsupported) and not has_supported_claim)
        return SynthesisResult(
            answer=" ".join(answer_parts),
            claims=supported,
            citations=validation.citations,
            unsupported_claims_removed=unsupported,
            conflicts=conflicts,
            abstained=partial and not has_supported_claim,
            confidence_category=ConfidenceCategory.MEDIUM if partial else ConfidenceCategory.HIGH,
            outcome=(
                AnswerOutcome.ANSWER_PARTIALLY_SUPPORTED
                if partial
                else AnswerOutcome.ANSWER_SUPPORTED
            ),
        )
    outcome = map_diagnosis_to_outcome(diagnosis, safety_blocked=False)
    return SynthesisResult(
        answer=_abstention_for_outcome(query, outcome),
        claims=claims,
        citations=[],
        unsupported_claims_removed=unsupported,
        conflicts=conflicts,
        abstained=True,
        confidence_category=ConfidenceCategory.NONE,
        outcome=outcome,
    )


def _synthesize_topic_list_answer(
    query: str, evidence: list[UnifiedEvidence]
) -> SynthesisResult | None:
    internal = [
        item for item in evidence if item.source_type == EvidenceSourceType.INTERNAL_DOCUMENT
    ]
    retrieved = [
        RetrievedEvidence(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            document_title=item.title,
            content=item.excerpt,
            score=item.retrieval_score or item.combined_score,
            metadata={"section": item.section} if item.section else {},
        )
        for item in internal
        if item.chunk_id is not None and item.document_id is not None
    ]
    topic_items = discover_topic_items(retrieved)
    if not topic_items and not has_practice_questions(retrieved):
        return None
    if not topic_items:
        return SynthesisResult(
            answer=topic_list_abstention_message(),
            claims=[],
            citations=[],
            unsupported_claims_removed=[],
            conflicts=[],
            abstained=True,
            confidence_category=ConfidenceCategory.NONE,
            outcome=AnswerOutcome.INSUFFICIENT_EVIDENCE,
        )
    claims: list[Claim] = []
    evidence_ids: list[str] = []
    by_chunk = {str(item.chunk_id): item for item in internal}
    for index, topic in enumerate(topic_items, 1):
        source = by_chunk.get(str(topic.chunk_id))
        if source is None:
            continue
        evidence_ids.append(source.evidence_id)
        claims.append(
            Claim(
                claim_id=f"T{index}",
                claim_text=f"{topic.label} is a covered topic.",
                supporting_evidence_ids=[source.evidence_id],
                contradicting_evidence_ids=[],
                support_score=1.0,
                verification_status=VerificationStatus.SUPPORTED,
            )
        )
    validation = validate_citations(
        _citations_for_evidence(evidence, evidence_ids), evidence, claims
    )
    return SynthesisResult(
        answer=synthesize_topic_list(topic_items),
        claims=claims,
        citations=validation.citations,
        unsupported_claims_removed=[],
        conflicts=[],
        abstained=False,
        confidence_category=ConfidenceCategory.HIGH,
        outcome=AnswerOutcome.ANSWER_SUPPORTED,
    )


def validate_citations(
    citations: list[dict[str, Any]], evidence: list[UnifiedEvidence], claims: list[Claim]
) -> CitationValidationResult:
    by_label = {item.citation_label: item for item in evidence}
    claim_evidence_ids = {
        evidence_id
        for claim in claims
        for evidence_id in [*claim.supporting_evidence_ids, *claim.contradicting_evidence_ids]
    }
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for citation in citations:
        label = str(citation.get("citation_label") or citation.get("external_source_label") or "")
        item = by_label.get(label)
        if item is None:
            rejected.append({"citation": citation, "reason": "unknown_label"})
            AGENT_CITATIONS_REJECTED.labels(outcome="unknown_label").inc()
            continue
        if item.evidence_id not in claim_evidence_ids:
            rejected.append({"citation": citation, "reason": "unused"})
            AGENT_CITATIONS_REJECTED.labels(outcome="unused").inc()
            continue
        if label in seen:
            continue
        seen.add(label)
        accepted.append(citation)
        AGENT_CITATIONS_VALIDATED.labels(
            source_type=item.source_type.value, outcome="accepted"
        ).inc()
    return CitationValidationResult(citations=accepted, rejected=rejected)


def map_diagnosis_to_outcome(
    diagnosis: dict[str, Any], *, safety_blocked: bool, has_conflict: bool = False
) -> AnswerOutcome:
    if safety_blocked:
        return AnswerOutcome.SAFETY_BLOCKED
    if has_conflict:
        return AnswerOutcome.CONFLICTING_EVIDENCE
    status = diagnosis.get("status")
    if status == DiagnosisStatus.KNOWLEDGE_ABSENT.value:
        return AnswerOutcome.KNOWLEDGE_ABSENT
    if status == DiagnosisStatus.AMBIGUOUS_QUERY.value:
        return AnswerOutcome.CLARIFICATION_REQUIRED
    if status == DiagnosisStatus.CONFLICTING_EVIDENCE.value:
        return AnswerOutcome.CONFLICTING_EVIDENCE
    if status == DiagnosisStatus.PARTIAL_EVIDENCE.value:
        return AnswerOutcome.ANSWER_PARTIALLY_SUPPORTED
    if status == DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED.value:
        return AnswerOutcome.INSUFFICIENT_EVIDENCE
    return AnswerOutcome.INSUFFICIENT_EVIDENCE


def _external_source_type(item: ExternalSource) -> EvidenceSourceType:
    if item.provider == "wikipedia" or item.source_type == "encyclopedia":
        return EvidenceSourceType.WIKIPEDIA
    if item.provider == "arxiv" or item.source_type == "research_paper":
        return EvidenceSourceType.ARXIV
    if item.source_type == "approved_api":
        return EvidenceSourceType.APPROVED_API
    return EvidenceSourceType.WEB_SEARCH


def _trust_score(source_type: EvidenceSourceType, provider: str) -> float:
    configured = settings.evidence_trust_weights
    if provider in configured:
        return configured[provider]
    return configured.get(source_type.value, 0.5)


def _freshness_score(publication_date: str | None) -> float:
    if not publication_date:
        return 0.5
    year_match = re.search(r"(19|20)\d{2}", publication_date)
    if not year_match:
        return 0.5
    year = int(year_match.group(0))
    current_year = datetime.now(UTC).year
    return max(0.1, min(1.0, 1.0 - ((current_year - year) / 10)))


def _rank_score(rank: int) -> float:
    return max(0.0, min(1.0, 1.0 / max(1, rank)))


def _dedupe_key(item: UnifiedEvidence) -> str:
    if item.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
        return (
            f"internal:{item.tenant_id}:{item.workspace_id}:{item.document_id}:"
            f"{item.document_version_id}:{item.chunk_id}"
        )
    if item.canonical_url:
        return f"url:{item.canonical_url.rstrip('/').lower()}"
    return f"text:{_content_fingerprint(item.title + ' ' + item.excerpt)}"


def _can_merge(left: UnifiedEvidence, right: UnifiedEvidence) -> bool:
    if left.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
        return (
            right.source_type == EvidenceSourceType.INTERNAL_DOCUMENT
            and left.tenant_id == right.tenant_id
            and left.workspace_id == right.workspace_id
        )
    if right.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
        return False
    return True


def _comparable(left: UnifiedEvidence, right: UnifiedEvidence) -> bool:
    left_projects = _project_names(f"{left.title} {left.excerpt}")
    right_projects = _project_names(f"{right.title} {right.excerpt}")
    if left_projects or right_projects:
        return bool(left_projects & right_projects)
    if left.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
        return left.tenant_id == right.tenant_id and left.workspace_id == right.workspace_id
    return (
        _term_overlap(left.title, right.title) > 0
        or _term_overlap(left.excerpt, right.excerpt) > 0.15
    )


def _query_comparable(query: str, item: UnifiedEvidence) -> bool:
    query_projects = _project_names(query)
    item_projects = _project_names(f"{item.title} {item.excerpt}")
    if query_projects:
        return bool(query_projects & item_projects)
    return _term_overlap(query, item.excerpt) >= 0.2


def _conflict_between(left: str, right: str) -> tuple[ConflictStatus, str]:
    left_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", left))
    right_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", right))
    if left_numbers and right_numbers and left_numbers != right_numbers:
        if not any(isclose(float(a), float(b)) for a in left_numbers for b in right_numbers):
            return ConflictStatus.CONFIRMED_CONFLICT, "numeric_value"
    date_pattern = (
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b"
        r"|\b20\d{2}-\d{2}-\d{2}\b"
    )
    left_dates = set(re.findall(date_pattern, left, re.I))
    right_dates = set(re.findall(date_pattern, right, re.I))
    if (
        left_dates
        and right_dates
        and {d.lower() for d in left_dates} != {d.lower() for d in right_dates}
    ):
        return ConflictStatus.CONFIRMED_CONFLICT, "date"
    status_pairs = [
        ("approved", "rejected"),
        ("enabled", "disabled"),
        ("active", "inactive"),
        ("launched", "not launched"),
        ("owned by", "not owned by"),
    ]
    left_lower = left.lower()
    right_lower = right.lower()
    if any(a in left_lower and b in right_lower for a, b in status_pairs) or any(
        b in left_lower and a in right_lower for a, b in status_pairs
    ):
        return ConflictStatus.CONFIRMED_CONFLICT, "opposing_status"
    owner_pattern = re.compile(
        r"(?:owned by|owner is|accountable to)\s+([A-Z][A-Za-z0-9 &-]{2,80})"
    )
    left_owner = owner_pattern.search(left)
    right_owner = owner_pattern.search(right)
    if left_owner and right_owner and left_owner.group(1).strip() != right_owner.group(1).strip():
        return ConflictStatus.CONFIRMED_CONFLICT, "owner_entity"
    if (
        re.search(r"\bnot\b|\bnever\b|\bno\b", left_lower)
        != bool(re.search(r"\bnot\b|\bnever\b|\bno\b", right_lower))
        and _term_overlap(left, right) > 0.3
    ):
        return ConflictStatus.POSSIBLE_CONFLICT, "negation"
    return ConflictStatus.NO_CONFLICT, "none"


def _self_conflict(value: str) -> tuple[ConflictStatus, str]:
    date_pattern = (
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b"
        r"|\b20\d{2}-\d{2}-\d{2}\b"
    )
    dates = {item.lower() for item in re.findall(date_pattern, value, re.I)}
    if len(dates) > 1:
        return ConflictStatus.CONFIRMED_CONFLICT, "date"
    status_pairs = [
        ("approved", "rejected"),
        ("enabled", "disabled"),
        ("active", "inactive"),
        ("launched", "not launched"),
    ]
    normalized = value.lower()
    if any(left in normalized and right in normalized for left, right in status_pairs):
        return ConflictStatus.CONFIRMED_CONFLICT, "opposing_status"
    return ConflictStatus.NO_CONFLICT, "none"


def _citations_for_evidence(
    evidence: list[UnifiedEvidence], evidence_ids: list[str]
) -> list[dict[str, Any]]:
    wanted = set(evidence_ids)
    citations: list[dict[str, Any]] = []
    for item in evidence:
        if item.evidence_id not in wanted:
            continue
        if item.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
            citations.append(
                {
                    "source": "internal",
                    "citation_label": item.citation_label,
                    "document_title": item.title,
                    "document_id": str(item.document_id),
                    "document_version_id": str(item.document_version_id)
                    if item.document_version_id
                    else None,
                    "chunk_id": str(item.chunk_id),
                    "page_number": item.page_number,
                    "section": item.section,
                    "excerpt": item.excerpt,
                }
            )
        else:
            citations.append(
                {
                    "source": "external",
                    "citation_label": item.citation_label,
                    "external_source_label": item.citation_label,
                    "provider": item.provider,
                    "title": item.title,
                    "canonical_url": item.canonical_url,
                    "retrieval_date": item.retrieval_timestamp.date().isoformat(),
                    "excerpt": item.excerpt,
                }
            )
    return citations


def _renumber_citations(evidence: list[UnifiedEvidence]) -> list[UnifiedEvidence]:
    internal = external = 0
    renumbered: list[UnifiedEvidence] = []
    for item in evidence:
        if item.source_type == EvidenceSourceType.INTERNAL_DOCUMENT:
            internal += 1
            label = f"D{internal}"
        else:
            external += 1
            label = f"E{external}"
        renumbered.append(item.model_copy(update={"citation_label": label}))
    return renumbered


def _support_score(query: str, claim_text: str, evidence: UnifiedEvidence) -> float:
    overlap = _term_overlap(query, claim_text)
    evidence_overlap = _term_overlap(query, evidence.excerpt)
    score = min(
        1.0,
        (overlap * 0.35)
        + (evidence_overlap * 0.35)
        + ((evidence.retrieval_score or 0.0) * 0.15)
        + (evidence.trust_score * 0.15),
    )
    normalized_query = query.lower()
    normalized_claim = claim_text.lower()
    ownership_terms = ("owned by", "owner is", "accountable to", "responsible")
    if any(term in normalized_query for term in ("who owns", "owner", "responsible")) and not any(
        term in normalized_claim for term in ownership_terms
    ):
        score *= 0.45
    return score


def _term_overlap(left: str, right: str) -> float:
    left_terms = key_terms(left)
    right_terms = key_terms(right)
    if not left_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms)


def _extract_claim_text(excerpt: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", excerpt.strip())
    return _compact_text(sentences[0] if sentences else excerpt, limit=600)


def _conflict_answer(evidence: list[UnifiedEvidence], conflicts: list[Conflict]) -> str:
    parts = ["The available evidence conflicts."]
    seen: set[str] = set()
    for conflict in conflicts:
        for evidence_id in conflict.evidence_ids:
            item = next(
                (candidate for candidate in evidence if candidate.evidence_id == evidence_id),
                None,
            )
            if item is None or evidence_id in seen:
                continue
            seen.add(evidence_id)
            parts.append(f"{item.excerpt} [{item.citation_label}]")
    parts.append("Please clarify which source or version should govern the answer.")
    return " ".join(parts)


def _abstention_for_outcome(query: str, outcome: AnswerOutcome) -> str:
    if outcome == AnswerOutcome.CLARIFICATION_REQUIRED:
        return f"I need a more specific question to answer: {query}"
    if outcome == AnswerOutcome.KNOWLEDGE_ABSENT:
        return "I could not find this in the available authorized evidence."
    return "I could not find sufficient evidence in the available authorized sources."


def _label_for(evidence_id: str, evidence: list[UnifiedEvidence]) -> str:
    for item in evidence:
        if item.evidence_id == evidence_id:
            return item.citation_label
    return "?"


def _compact_text(value: str, limit: int = 1800) -> str:
    compacted = re.sub(r"\s+", " ", value).strip()
    return compacted[:limit].rstrip()


def _content_fingerprint(value: str) -> str:
    normalized = re.sub(r"\W+", " ", value.lower()).strip()
    return sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _stable_digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _counts_by_source(evidence: list[UnifiedEvidence]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in evidence:
        counts[item.source_type.value] += 1
    return dict(counts)


def _uuid_or_none(value: Any) -> UUID | None:
    if value in {None, ""}:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    return str(value) if value not in {None, ""} else None


def _is_time_sensitive(query: str) -> bool:
    normalized = query.lower()
    return any(term in normalized for term in ("latest", "current", "today", "recent", "newest"))


def _project_names(value: str) -> set[str]:
    return {match.lower() for match in re.findall(r"\bProject\s+[A-Z][A-Za-z0-9-]+\b", value)}
