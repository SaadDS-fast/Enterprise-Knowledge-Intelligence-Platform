from app.evaluation.retrieval_diagnosis import evaluate_diagnosis_predictions


def test_retrieval_diagnosis_metrics_are_measured_from_cases():
    cases = [
        {
            "expected_status": "SUFFICIENT_EVIDENCE",
            "actual_status": "SUFFICIENT_EVIDENCE",
            "expected_abstained": False,
            "actual_abstained": False,
            "retrieval_attempts": 1,
        },
        {
            "expected_status": "KNOWLEDGE_ABSENT",
            "actual_status": "KNOWLEDGE_ABSENT",
            "expected_abstained": True,
            "actual_abstained": True,
            "retrieval_attempts": 2,
        },
        {
            "expected_status": "RETRIEVAL_FAILURE_RECOVERED",
            "actual_status": "KNOWLEDGE_ABSENT",
            "expected_abstained": False,
            "actual_abstained": True,
            "retrieval_attempts": 2,
        },
    ]

    metrics = evaluate_diagnosis_predictions(cases)

    assert metrics["case_count"] == 3
    assert metrics["diagnosis_accuracy"] == 2 / 3
    assert metrics["knowledge_absence_detection_accuracy"] == 1.0
    assert metrics["false_knowledge_absence_rate"] == 1 / 3
    assert metrics["false_abstention_rate"] == 1 / 3
    assert metrics["average_retrieval_attempts"] == 5 / 3
