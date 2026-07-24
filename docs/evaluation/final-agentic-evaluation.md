# Final Agentic Evaluation

Historical baseline retained from the prior executed fixture:

- support rate: 0.5
- citation precision: 1.0
- citation recall: 0.75
- unsupported claim rate: 0.3333
- abstention accuracy: 1.0
- conflict detection accuracy: 1.0
- average evidence count: 2.5

The expanded deterministic release fixture covers supported answers, multi-document support,
partial support, unsupported questions, retrieval failure, knowledge absence, ambiguity,
numeric/date/entity conflicts, internal/external agreement and conflict, stale/duplicate/misleading
sources, prompt injection, tenant isolation, citation mismatch, and report citation integrity.

Deterministic-core hardening adds a targeted internal-document regression set for:

- direct heading/value extraction, including `Topic: Functions`
- non-conflict handling for unrelated profile or teaching-method facts
- genuine same-attribute topic conflicts
- normalized expected/actual answer value matching
- citation validity and evidence-support reporting in evaluation results

Evaluation distinguishes workflow completion from answer support. A completed run may still be an
abstention, conflict, knowledge absence, or failure.

Executed target checks are in `backend/tests/unit/test_multi_source_evaluation.py`.
This is a deterministic local evaluation, not a claim of enterprise-scale benchmark performance.

Final 2026-07-23 release fixture result:

- deterministic release cases: 18
- citation precision threshold: >= 0.95, passed
- citation recall threshold: >= 0.85, passed
- unsupported claim rate threshold: <= 0.15, passed
- abstention, conflict, knowledge-absence, retrieval-failure, and source-selection accuracy thresholds: >= 0.90, passed
- tenant isolation success rate: 1.0
