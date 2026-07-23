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


def test_final_agentic_evaluation_metrics_cover_release_cases() -> None:
    cases = [
        {
            "outcome": outcome,
            "expected_citation_labels": ["D1", "D2"] if actual_citations else [],
            "actual_citation_labels": actual_citations,
            "claim_count": 2,
            "unsupported_claim_count": unsupported_claims,
            "expected_abstained": expected_abstained,
            "actual_abstained": expected_abstained,
            "expected_conflict": expected_conflict,
            "actual_conflict": expected_conflict,
            "expected_knowledge_absent": expected_absent,
            "actual_knowledge_absent": expected_absent,
            "expected_retrieval_failure": expected_retrieval_failure,
            "actual_retrieval_failure": expected_retrieval_failure,
            "expected_source_selection": source_selection,
            "actual_source_selection": source_selection,
            "tenant_isolation_passed": True,
            "evidence_count": evidence_count,
            "tool_call_count": tool_calls,
            "latency_ms": latency_ms,
        }
        for (
            outcome,
            actual_citations,
            unsupported_claims,
            expected_abstained,
            expected_conflict,
            expected_absent,
            expected_retrieval_failure,
            source_selection,
            evidence_count,
            tool_calls,
            latency_ms,
        ) in [
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "internal",
                2,
                6,
                110,
            ),
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "multi_document",
                3,
                7,
                130,
            ),
            (
                "ANSWER_PARTIALLY_SUPPORTED",
                ["D1"],
                1,
                True,
                False,
                False,
                False,
                "internal",
                2,
                8,
                140,
            ),
            ("KNOWLEDGE_ABSENT", [], 0, True, False, True, False, "none", 0, 5, 90),
            ("INSUFFICIENT_EVIDENCE", [], 1, True, False, False, True, "none", 0, 8, 160),
            ("CLARIFICATION_REQUIRED", [], 0, True, False, False, False, "none", 1, 4, 80),
            (
                "CONFLICTING_EVIDENCE",
                ["D1", "D2"],
                0,
                True,
                True,
                False,
                False,
                "internal",
                2,
                8,
                150,
            ),
            (
                "CONFLICTING_EVIDENCE",
                ["D1", "D2"],
                0,
                True,
                True,
                False,
                False,
                "internal",
                2,
                8,
                150,
            ),
            (
                "CONFLICTING_EVIDENCE",
                ["D1", "D2"],
                0,
                True,
                True,
                False,
                False,
                "internal",
                2,
                8,
                150,
            ),
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "internal_external",
                3,
                9,
                190,
            ),
            (
                "CONFLICTING_EVIDENCE",
                ["D1", "D2"],
                0,
                True,
                True,
                False,
                False,
                "internal_external",
                3,
                9,
                210,
            ),
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "fresh_internal",
                2,
                8,
                170,
            ),
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "deduplicated",
                2,
                8,
                165,
            ),
            (
                "ANSWER_PARTIALLY_SUPPORTED",
                ["D1"],
                1,
                True,
                False,
                False,
                False,
                "internal",
                2,
                8,
                155,
            ),
            ("SAFETY_BLOCKED", [], 0, True, False, False, False, "none", 1, 5, 120),
            ("INSUFFICIENT_EVIDENCE", [], 0, True, False, False, False, "none", 0, 3, 70),
            ("INSUFFICIENT_EVIDENCE", [], 1, True, False, False, False, "none", 1, 6, 110),
            (
                "ANSWER_SUPPORTED",
                ["D1", "D2"],
                0,
                False,
                False,
                False,
                False,
                "research_report",
                4,
                10,
                260,
            ),
        ]
    ]

    metrics = evaluate_multi_source_runs(cases)

    assert metrics["case_count"] == 18
    assert metrics["citation_precision"] >= 0.95
    assert metrics["citation_recall"] >= 0.85
    assert metrics["unsupported_claim_rate"] <= 0.15
    assert metrics["abstention_accuracy"] >= 0.90
    assert metrics["conflict_detection_accuracy"] >= 0.90
    assert metrics["knowledge_absence_accuracy"] >= 0.90
    assert metrics["retrieval_failure_diagnosis_accuracy"] >= 0.90
    assert metrics["source_selection_accuracy"] >= 0.90
    assert metrics["tenant_isolation_success_rate"] == 1.0
