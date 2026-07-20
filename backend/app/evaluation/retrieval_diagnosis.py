from __future__ import annotations

from collections import Counter


def evaluate_diagnosis_predictions(cases: list[dict]) -> dict[str, float | int]:
    if not cases:
        return {
            "case_count": 0,
            "diagnosis_accuracy": 0.0,
            "retry_recovery_rate": 0.0,
            "knowledge_absence_detection_accuracy": 0.0,
            "false_knowledge_absence_rate": 0.0,
            "false_retrieval_failure_rate": 0.0,
            "abstention_accuracy": 0.0,
            "false_abstention_rate": 0.0,
            "average_retrieval_attempts": 0.0,
        }
    counts = Counter()
    attempts = 0
    for case in cases:
        expected = case["expected_status"]
        actual = case["actual_status"]
        expected_abstain = bool(case.get("expected_abstained", False))
        actual_abstain = bool(case.get("actual_abstained", False))
        attempts += int(case.get("retrieval_attempts", 1))
        counts["correct"] += expected == actual
        counts["retry_expected"] += expected == "RETRIEVAL_FAILURE_RECOVERED"
        counts["retry_recovered"] += (
            expected == "RETRIEVAL_FAILURE_RECOVERED" and actual == expected
        )
        counts["absence_expected"] += expected == "KNOWLEDGE_ABSENT"
        counts["absence_correct"] += expected == "KNOWLEDGE_ABSENT" and actual == expected
        counts["false_absence"] += expected != "KNOWLEDGE_ABSENT" and actual == "KNOWLEDGE_ABSENT"
        counts["false_retrieval_failure"] += not expected.startswith(
            "RETRIEVAL_FAILURE"
        ) and actual.startswith("RETRIEVAL_FAILURE")
        counts["abstention_correct"] += expected_abstain == actual_abstain
        counts["false_abstention"] += not expected_abstain and actual_abstain

    total = len(cases)
    return {
        "case_count": total,
        "diagnosis_accuracy": counts["correct"] / total,
        "retry_recovery_rate": counts["retry_recovered"] / max(1, counts["retry_expected"]),
        "knowledge_absence_detection_accuracy": counts["absence_correct"]
        / max(1, counts["absence_expected"]),
        "false_knowledge_absence_rate": counts["false_absence"] / total,
        "false_retrieval_failure_rate": counts["false_retrieval_failure"] / total,
        "abstention_accuracy": counts["abstention_correct"] / total,
        "false_abstention_rate": counts["false_abstention"] / total,
        "average_retrieval_attempts": attempts / total,
    }
