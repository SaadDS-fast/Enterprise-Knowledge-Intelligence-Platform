from uuid import uuid4

from app.models.domain import RetrievedEvidence
from app.rag.evidence_diagnosis import (
    DiagnosisStatus,
    diagnose_evidence,
    reformulate_query,
    support_score,
)


def evidence(content: str, score: float = 0.82, title: str = "Atlas Brief") -> RetrievedEvidence:
    return RetrievedEvidence(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        content=content,
        score=score,
        metadata={},
    )


def test_diagnosis_sufficient_initial_evidence():
    items = [evidence("Project Atlas was launched in March 2025.")]

    diagnosis = diagnose_evidence(
        query="When was Project Atlas launched?",
        initial_evidence=items,
        final_evidence=items,
        initial_evidence_sufficient=True,
        final_evidence_sufficient=True,
        retry_performed=False,
        retry_strategy=[],
    )

    assert diagnosis.status is DiagnosisStatus.SUFFICIENT_EVIDENCE
    assert diagnosis.retry_performed is False


def test_diagnosis_retrieval_failure_recovered():
    initial = [evidence("Project Atlas budget notes.", 0.31)]
    final = [evidence("Project Atlas was launched in March 2025.", 0.91)]

    diagnosis = diagnose_evidence(
        query="When was Project Atlas launched?",
        initial_evidence=initial,
        final_evidence=final,
        initial_evidence_sufficient=False,
        final_evidence_sufficient=True,
        retry_performed=True,
        retry_strategy=["query_reformulation", "top_k_expansion"],
    )

    assert diagnosis.status is DiagnosisStatus.RETRIEVAL_FAILURE_RECOVERED
    assert diagnosis.final_support_score > diagnosis.initial_support_score


def test_diagnosis_knowledge_absent():
    diagnosis = diagnose_evidence(
        query="Who approved Project Atlas procurement?",
        initial_evidence=[],
        final_evidence=[],
        initial_evidence_sufficient=False,
        final_evidence_sufficient=False,
        retry_performed=True,
        retry_strategy=["query_reformulation", "top_k_expansion"],
    )

    assert diagnosis.status is DiagnosisStatus.KNOWLEDGE_ABSENT


def test_diagnosis_partial_evidence():
    items = [evidence("Project Atlas was launched in March 2025.", 0.43)]

    diagnosis = diagnose_evidence(
        query="When was Project Atlas launched and who approved procurement?",
        initial_evidence=items,
        final_evidence=items,
        initial_evidence_sufficient=False,
        final_evidence_sufficient=False,
        retry_performed=False,
        retry_strategy=[],
    )

    assert diagnosis.status is DiagnosisStatus.PARTIAL_EVIDENCE


def test_diagnosis_conflicting_evidence_for_date_query():
    items = [
        evidence("Project Atlas was launched in March 2025.", 0.8, "Atlas A"),
        evidence("Project Atlas was launched in March 2026.", 0.79, "Atlas B"),
    ]

    diagnosis = diagnose_evidence(
        query="When was Project Atlas launched?",
        initial_evidence=items,
        final_evidence=items,
        initial_evidence_sufficient=False,
        final_evidence_sufficient=False,
        retry_performed=True,
        retry_strategy=["top_k_expansion"],
    )

    assert diagnosis.status is DiagnosisStatus.CONFLICTING_EVIDENCE


def test_diagnosis_ambiguous_query():
    diagnosis = diagnose_evidence(
        query="Atlas?",
        initial_evidence=[],
        final_evidence=[],
        initial_evidence_sufficient=False,
        final_evidence_sufficient=False,
        retry_performed=True,
        retry_strategy=["query_reformulation"],
    )

    assert diagnosis.status is DiagnosisStatus.AMBIGUOUS_QUERY


def test_reformulation_adds_local_synonyms():
    reformulated = reformulate_query("Who is responsible for Atlas?")

    assert "owner" in reformulated
    assert "accountable" in reformulated


def test_support_score_uses_query_coverage_and_retrieval_score():
    score = support_score(
        "When was Project Atlas launched?",
        [evidence("Project Atlas was launched in March 2025.", 0.7)],
    )

    assert score > 0.5
