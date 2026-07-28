from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.rag.evidence import SupportAssessment, SupportStatus
from app.rag.query_intent import QueryIntent


class SufficiencyDecision(StrEnum):
    SUFFICIENT_DIRECT = "SUFFICIENT_DIRECT"
    SUFFICIENT_COMPOSITE = "SUFFICIENT_COMPOSITE"
    RETRIEVAL_RETRY_REQUIRED = "RETRIEVAL_RETRY_REQUIRED"
    RETRIEVAL_FAILURE_UNRESOLVED = "RETRIEVAL_FAILURE_UNRESOLVED"
    KNOWLEDGE_ABSENT = "KNOWLEDGE_ABSENT"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    LOW_QUALITY_SOURCE = "LOW_QUALITY_SOURCE"


@dataclass(frozen=True, slots=True)
class SufficiencyAssessment:
    decision: SufficiencyDecision
    sufficient: bool
    reason: str


def assess_sufficiency(
    *,
    intent: QueryIntent,
    support: SupportAssessment,
    candidate_count: int,
    retry_performed: bool,
    low_quality: bool = False,
) -> SufficiencyAssessment:
    if intent is QueryIntent.AMBIGUOUS:
        return SufficiencyAssessment(SufficiencyDecision.AMBIGUOUS_QUERY, False, "ambiguous")
    if low_quality:
        return SufficiencyAssessment(
            SufficiencyDecision.LOW_QUALITY_SOURCE, False, "low_quality_source"
        )
    if support.status is SupportStatus.SUPPORTED:
        composite = intent in {QueryIntent.COMPARISON, QueryIntent.MULTI_EVIDENCE}
        distinct_sources = len({fact.source_index for fact in support.facts})
        if intent is QueryIntent.COMPARISON and distinct_sources < 2:
            return SufficiencyAssessment(
                SufficiencyDecision.RETRIEVAL_FAILURE_UNRESOLVED,
                False,
                "incomplete_composite",
            )
        return SufficiencyAssessment(
            SufficiencyDecision.SUFFICIENT_COMPOSITE
            if composite
            else SufficiencyDecision.SUFFICIENT_DIRECT,
            True,
            "claim_mapped_to_evidence",
        )
    if not retry_performed:
        return SufficiencyAssessment(
            SufficiencyDecision.RETRIEVAL_RETRY_REQUIRED, False, "retry_required"
        )
    if (
        support.status is SupportStatus.ABSENT
        or candidate_count == 0
        or (intent is QueryIntent.KNOWLEDGE_ABSENCE_PROBE and not support.facts)
    ):
        return SufficiencyAssessment(
            SufficiencyDecision.KNOWLEDGE_ABSENT, False, "no_supported_fact"
        )
    return SufficiencyAssessment(
        SufficiencyDecision.RETRIEVAL_FAILURE_UNRESOLVED,
        False,
        "partial_support_only",
    )
