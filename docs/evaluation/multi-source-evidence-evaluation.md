# Multi-Source Evidence Evaluation

Updated on 2026-07-22.

## Purpose

The multi-source evaluation runner compares executed cases from:

1. Existing adaptive RAG
2. Internal-only controlled agent
3. Multi-source controlled agent

It does not invent results. Metrics are produced only from supplied case outputs.

## Metrics

`backend/app/evaluation/multi_source_evidence.py` measures:

- answer support rate
- citation precision
- citation recall
- unsupported claim rate
- abstention accuracy
- conflict detection accuracy
- average evidence count
- average tool calls
- average latency

## Case Inputs

Each executed case can provide:

- `outcome`
- `expected_citation_labels`
- `actual_citation_labels`
- `claim_count`
- `unsupported_claim_count`
- `expected_abstained`
- `actual_abstained`
- `expected_conflict`
- `actual_conflict`
- `evidence_count`
- `tool_call_count`
- `latency_ms`

## Current Executed Result

The deterministic unit test `tests/unit/test_multi_source_evaluation.py` verifies metric calculation on two synthetic executed cases:

- `case_count`: 2
- `answer_support_rate`: 0.5
- `citation_precision`: 1.0
- `citation_recall`: 0.75
- `unsupported_claim_rate`: 0.3333
- `abstention_accuracy`: 1.0
- `conflict_detection_accuracy`: 1.0
- `average_evidence_count`: 2.5

These are test-fixture metrics only, not platform benchmark claims.
