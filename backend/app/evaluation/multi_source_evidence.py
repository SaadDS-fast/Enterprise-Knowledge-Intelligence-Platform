from __future__ import annotations

from statistics import mean
from typing import Any


def evaluate_multi_source_runs(cases: list[dict[str, Any]]) -> dict[str, float | int]:
    if not cases:
        return {
            "case_count": 0,
            "answer_support_rate": 0.0,
            "citation_precision": 0.0,
            "citation_recall": 0.0,
            "unsupported_claim_rate": 0.0,
            "abstention_accuracy": 0.0,
            "conflict_detection_accuracy": 0.0,
            "knowledge_absence_accuracy": 0.0,
            "retrieval_failure_diagnosis_accuracy": 0.0,
            "source_selection_accuracy": 0.0,
            "tenant_isolation_success_rate": 0.0,
            "average_evidence_count": 0.0,
            "average_tool_calls": 0.0,
            "average_latency_ms": 0.0,
        }

    supported = 0
    citation_precision_scores: list[float] = []
    citation_recall_scores: list[float] = []
    unsupported_claims = 0
    total_claims = 0
    abstention_correct = 0
    conflict_correct = 0
    knowledge_absence_correct = 0
    retrieval_failure_correct = 0
    source_selection_correct = 0
    tenant_isolation_passed = 0
    evidence_counts: list[int] = []
    tool_calls: list[int] = []
    latencies: list[int] = []

    for case in cases:
        expected_citations = set(case.get("expected_citation_labels", []))
        actual_citations = set(case.get("actual_citation_labels", []))
        if expected_citations or actual_citations:
            true_positive = len(expected_citations & actual_citations)
            citation_precision_scores.append(true_positive / max(1, len(actual_citations)))
            citation_recall_scores.append(true_positive / max(1, len(expected_citations)))

        outcome = str(case.get("outcome", ""))
        supported += outcome in {"ANSWER_SUPPORTED", "ANSWER_PARTIALLY_SUPPORTED"}
        unsupported_claims += int(case.get("unsupported_claim_count", 0))
        total_claims += int(case.get("claim_count", 0))
        abstention_correct += bool(case.get("expected_abstained")) == bool(
            case.get("actual_abstained")
        )
        conflict_correct += bool(case.get("expected_conflict")) == bool(case.get("actual_conflict"))
        knowledge_absence_correct += bool(case.get("expected_knowledge_absent")) == bool(
            case.get("actual_knowledge_absent")
        )
        retrieval_failure_correct += bool(case.get("expected_retrieval_failure")) == bool(
            case.get("actual_retrieval_failure")
        )
        source_selection_correct += str(case.get("expected_source_selection", "")) == str(
            case.get("actual_source_selection", "")
        )
        tenant_isolation_passed += bool(case.get("tenant_isolation_passed", True))
        evidence_counts.append(int(case.get("evidence_count", 0)))
        tool_calls.append(int(case.get("tool_call_count", 0)))
        latencies.append(int(case.get("latency_ms", 0)))

    total = len(cases)
    return {
        "case_count": total,
        "answer_support_rate": supported / total,
        "citation_precision": mean(citation_precision_scores) if citation_precision_scores else 0.0,
        "citation_recall": mean(citation_recall_scores) if citation_recall_scores else 0.0,
        "unsupported_claim_rate": unsupported_claims / max(1, total_claims),
        "abstention_accuracy": abstention_correct / total,
        "conflict_detection_accuracy": conflict_correct / total,
        "knowledge_absence_accuracy": knowledge_absence_correct / total,
        "retrieval_failure_diagnosis_accuracy": retrieval_failure_correct / total,
        "source_selection_accuracy": source_selection_correct / total,
        "tenant_isolation_success_rate": tenant_isolation_passed / total,
        "average_evidence_count": mean(evidence_counts),
        "average_tool_calls": mean(tool_calls),
        "average_latency_ms": mean(latencies),
    }
