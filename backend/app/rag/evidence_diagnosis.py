from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.models.domain import RetrievedEvidence
from app.rag.evidence import key_terms


class DiagnosisStatus(StrEnum):
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    RETRIEVAL_FAILURE_RECOVERED = "RETRIEVAL_FAILURE_RECOVERED"
    RETRIEVAL_FAILURE_UNRESOLVED = "RETRIEVAL_FAILURE_UNRESOLVED"
    KNOWLEDGE_ABSENT = "KNOWLEDGE_ABSENT"
    PARTIAL_EVIDENCE = "PARTIAL_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"


class DiagnosisReason(StrEnum):
    INITIAL_SUPPORTING_EVIDENCE = "INITIAL_SUPPORTING_EVIDENCE"
    RETRY_FOUND_SUPPORTING_EVIDENCE = "RETRY_FOUND_SUPPORTING_EVIDENCE"
    RETRY_IMPROVED_WITHOUT_SUFFICIENT_SUPPORT = "RETRY_IMPROVED_WITHOUT_SUFFICIENT_SUPPORT"
    NO_RELEVANT_EVIDENCE_FOUND = "NO_RELEVANT_EVIDENCE_FOUND"
    SOME_QUERY_TERMS_SUPPORTED = "SOME_QUERY_TERMS_SUPPORTED"
    CONFLICTING_NUMERIC_OR_NEGATION_SIGNALS = "CONFLICTING_NUMERIC_OR_NEGATION_SIGNALS"
    QUERY_TOO_BROAD = "QUERY_TOO_BROAD"


@dataclass(frozen=True, slots=True)
class EvidenceDiagnosis:
    status: DiagnosisStatus
    initial_evidence_sufficient: bool
    retry_performed: bool
    retry_strategy: list[str]
    initial_support_score: float
    final_support_score: float
    evidence_count: int
    reason_code: DiagnosisReason

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "initial_evidence_sufficient": self.initial_evidence_sufficient,
            "retry_performed": self.retry_performed,
            "retry_strategy": self.retry_strategy,
            "initial_support_score": round(self.initial_support_score, 4),
            "final_support_score": round(self.final_support_score, 4),
            "evidence_count": self.evidence_count,
            "reason_code": self.reason_code.value,
        }


SYNONYMS = {
    "began": "launched started initiated",
    "begin": "launch start initiate",
    "budget": "cost funding allocation approved",
    "owned": "owner responsible accountable",
    "owner": "owned responsible accountable team",
    "responsible": "owner owned accountable team",
    "q1": "first quarter january february march",
}

NEGATION_TERMS = {"not", "never", "no", "denied", "cancelled", "canceled"}


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip().rstrip("?")


def reformulate_query(query: str) -> str:
    normalized = normalize_query(query)
    additions: list[str] = []
    for term in key_terms(normalized):
        if term in SYNONYMS:
            additions.append(SYNONYMS[term])
    return f"{normalized} {' '.join(additions)}".strip()


def support_score(query: str, evidence: list[RetrievedEvidence]) -> float:
    if not evidence:
        return 0.0
    terms = key_terms(query)
    if not terms:
        return max((item.score for item in evidence), default=0.0)
    evidence_terms = key_terms(" ".join(item.content for item in evidence[:5]))
    coverage = len(terms & evidence_terms) / len(terms)
    score = max((item.score for item in evidence), default=0.0)
    count_bonus = min(len(evidence), 3) * 0.04
    return max(0.0, min(1.0, 0.58 * score + 0.34 * coverage + count_bonus))


def has_conflicting_signals(query: str, evidence: list[RetrievedEvidence]) -> bool:
    contents = [item.content.lower() for item in evidence[:5]]
    if len(contents) < 2:
        return False
    joined = " ".join(contents)
    terms = key_terms(query)
    has_negation = any(term in key_terms(joined) for term in NEGATION_TERMS)
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", joined))
    numbers = {
        item.replace(",", "")
        for item in re.findall(r"\b\d+(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b", joined)
    }
    asks_date = bool(terms & {"launched", "launch", "began", "started", "date", "when"})
    asks_budget = bool(terms & {"budget", "cost", "funding", "allocation"})
    return has_negation or (asks_date and len(years) > 1) or (asks_budget and len(numbers) > 1)


def is_ambiguous_query(query: str) -> bool:
    terms = key_terms(query)
    return len(terms) <= 1 or normalize_query(query).lower() in {"atlas", "project", "status"}


def diagnose_evidence(
    *,
    query: str,
    initial_evidence: list[RetrievedEvidence],
    final_evidence: list[RetrievedEvidence],
    initial_evidence_sufficient: bool,
    final_evidence_sufficient: bool,
    retry_performed: bool,
    retry_strategy: list[str],
) -> EvidenceDiagnosis:
    initial_score = support_score(query, initial_evidence)
    final_score = support_score(query, final_evidence)

    if is_ambiguous_query(query):
        return EvidenceDiagnosis(
            status=DiagnosisStatus.AMBIGUOUS_QUERY,
            initial_evidence_sufficient=initial_evidence_sufficient,
            retry_performed=retry_performed,
            retry_strategy=retry_strategy,
            initial_support_score=initial_score,
            final_support_score=final_score,
            evidence_count=len(final_evidence),
            reason_code=DiagnosisReason.QUERY_TOO_BROAD,
        )
    if final_evidence and has_conflicting_signals(query, final_evidence):
        return EvidenceDiagnosis(
            status=DiagnosisStatus.CONFLICTING_EVIDENCE,
            initial_evidence_sufficient=initial_evidence_sufficient,
            retry_performed=retry_performed,
            retry_strategy=retry_strategy,
            initial_support_score=initial_score,
            final_support_score=final_score,
            evidence_count=len(final_evidence),
            reason_code=DiagnosisReason.CONFLICTING_NUMERIC_OR_NEGATION_SIGNALS,
        )
    if initial_evidence_sufficient:
        return EvidenceDiagnosis(
            status=DiagnosisStatus.SUFFICIENT_EVIDENCE,
            initial_evidence_sufficient=True,
            retry_performed=retry_performed,
            retry_strategy=retry_strategy,
            initial_support_score=initial_score,
            final_support_score=final_score,
            evidence_count=len(final_evidence),
            reason_code=DiagnosisReason.INITIAL_SUPPORTING_EVIDENCE,
        )
    if retry_performed and final_evidence_sufficient:
        return EvidenceDiagnosis(
            status=DiagnosisStatus.RETRIEVAL_FAILURE_RECOVERED,
            initial_evidence_sufficient=False,
            retry_performed=True,
            retry_strategy=retry_strategy,
            initial_support_score=initial_score,
            final_support_score=final_score,
            evidence_count=len(final_evidence),
            reason_code=DiagnosisReason.RETRY_FOUND_SUPPORTING_EVIDENCE,
        )
    if final_score >= 0.28 and final_evidence:
        status = (
            DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED
            if retry_performed and final_score > initial_score + 0.05
            else DiagnosisStatus.PARTIAL_EVIDENCE
        )
        return EvidenceDiagnosis(
            status=status,
            initial_evidence_sufficient=False,
            retry_performed=retry_performed,
            retry_strategy=retry_strategy,
            initial_support_score=initial_score,
            final_support_score=final_score,
            evidence_count=len(final_evidence),
            reason_code=(
                DiagnosisReason.RETRY_IMPROVED_WITHOUT_SUFFICIENT_SUPPORT
                if status is DiagnosisStatus.RETRIEVAL_FAILURE_UNRESOLVED
                else DiagnosisReason.SOME_QUERY_TERMS_SUPPORTED
            ),
        )
    return EvidenceDiagnosis(
        status=DiagnosisStatus.KNOWLEDGE_ABSENT,
        initial_evidence_sufficient=False,
        retry_performed=retry_performed,
        retry_strategy=retry_strategy,
        initial_support_score=initial_score,
        final_support_score=final_score,
        evidence_count=len(final_evidence),
        reason_code=DiagnosisReason.NO_RELEVANT_EVIDENCE_FOUND,
    )


def merge_evidence(
    initial_evidence: list[RetrievedEvidence], retry_evidence: list[RetrievedEvidence]
) -> list[RetrievedEvidence]:
    by_chunk = {item.chunk_id: item for item in initial_evidence}
    for item in retry_evidence:
        current = by_chunk.get(item.chunk_id)
        if current is None or item.score > current.score:
            by_chunk[item.chunk_id] = item
    return sorted(by_chunk.values(), key=lambda item: item.score, reverse=True)
