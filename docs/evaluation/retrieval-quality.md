# Retrieval quality evaluation

Phase 2 evaluation compares four named modes: lexical-only, deterministic hybrid,
semantic hybrid, and semantic hybrid plus reranker. A valid comparison uses fresh
documents indexed with the model version being measured and an operator-provisioned
local model.

The evaluation vocabulary includes Recall@1, Recall@3, Recall@5, MRR, nDCG@5, citation
precision and recall, answer support, unsupported claims, knowledge-absence accuracy,
recovery accuracy, tenant-isolation pass rate, average/p95 retrieval latency, model load
time, and peak memory where practical. `app.evaluation.retrieval_metrics` provides the
ranked retrieval metrics without replacing historical generation or multi-source
metrics.

Normal CI uses deterministic providers. It proves contracts, batching, normalization,
version checks, fallbacks, scoping, and stable ranking; it does not prove semantic model
quality. Live-model results must state the exact aliases, fresh-index condition, latency,
and whether the model cache was already provisioned. If it is not provisioned, report
the live comparison as `PARTIAL` and do not claim improvement.
Required corpus cases cover paraphrased meal allowance, indirect function definition,
kinematics practice questions, composite-wire deformation, absent annual revenue, and a
multi-document answer. Every case also asserts selected-document and tenant isolation.
