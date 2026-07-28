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

## 2026-07-28 live results

The fresh synthetic corpus contains 12 Tenant A and 2 overlapping Tenant B documents,
with 9 queries (8 positive, including paraphrases, comparison and distractors). Full
safe output is preserved in `phase2-live-results.json`.

| Mode | R@1 | R@3 | R@5 | MRR | nDCG@5 | Avg / p50 / p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| Lexical | .9375 | .9375 | .9375 | 1.0000 | .9516 | .196 / .187 / .291 |
| Deterministic hybrid | .9375 | .9375 | 1.0000 | 1.0000 | .9813 | .289 / .288 / .312 |
| Live semantic | .9375 | .9375 | 1.0000 | 1.0000 | .9813 | 7.743 / 7.530 / 9.439 |
| Live semantic + reranker | .8125 | 1.0000 | 1.0000 | .9375 | .9539 | 17.621 / 16.817 / 21.100 |

Citation precision/recall were .8000/.8889, support .8750, unsupported claims .2222,
recovery 1.0000, and isolation 1.0000 in every mode. Absence accuracy was .0000.
Semantic Recall@5 improved over lexical, but the cross-encoder harmed Recall@1/MRR;
therefore the release status is partial and no blanket improvement is claimed.
