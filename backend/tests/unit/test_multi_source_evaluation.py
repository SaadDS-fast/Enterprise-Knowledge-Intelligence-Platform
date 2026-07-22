from __future__ import annotations

from app.evaluation.multi_source_evidence import evaluate_multi_source_runs


def test_multi_source_evaluation_metrics_are_measured_from_cases() -> None:
    metrics = evaluate_multi_source_runs(
        [
            {
                "outcome": "ANSWER_SUPPORTED",
                "expected_citation_labels": ["D1"],
                "actual_citation_labels": ["D1"],
                "claim_count": 1,
                "unsupported_claim_count": 0,
                "expected_abstained": False,
                "actual_abstained": False,
                "expected_conflict": False,
                "actual_conflict": False,
                "evidence_count": 2,
                "tool_call_count": 7,
                "latency_ms": 120,
            },
            {
                "outcome": "CONFLICTING_EVIDENCE",
                "expected_citation_labels": ["D1", "E1"],
                "actual_citation_labels": ["D1"],
                "claim_count": 2,
                "unsupported_claim_count": 1,
                "expected_abstained": True,
                "actual_abstained": True,
                "expected_conflict": True,
                "actual_conflict": True,
                "evidence_count": 3,
                "tool_call_count": 8,
                "latency_ms": 180,
            },
        ]
    )
    assert metrics["case_count"] == 2
    assert metrics["answer_support_rate"] == 0.5
    assert metrics["citation_precision"] == 1.0
    assert metrics["citation_recall"] == 0.75
    assert metrics["unsupported_claim_rate"] == 1 / 3
    assert metrics["abstention_accuracy"] == 1.0
    assert metrics["conflict_detection_accuracy"] == 1.0
    assert metrics["average_evidence_count"] == 2.5
