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

## Calibration benchmark v1

Development contains 60 queries; holdout contains 40 and was executed once after
freezing `.45/.55` fusion, `.25` reranker blend, `.08` margin, top-N 20 and return-K 8.

| Holdout mode | R@1 | R@3 | R@5 | MRR | nDCG@5 |
|---|---:|---:|---:|---:|---:|
| Lexical | .6562 | .8438 | .8750 | .7714 | .7880 |
| Semantic hybrid | .7812 | .8750 | 1.0000 | .8594 | .8942 |
| Calibrated reranker | .9375 | .9688 | .9688 | .9570 | .9572 |

Calibrated citation precision/recall were `1.0000/.9688`, support `.9375`,
unsupported claims `.0000`, absence `1.0000`, recovery `.9688`, and isolation `1.0000`.
Because Recall@5 and support missed acceptance, status is partial. The consumed holdout
must not be used for further tuning.

## Blind holdout v2

The v2 fixture contains 120 new queries across 15 equally sized categories and has
SHA-256 `16dc10caf8b9608d60abf84f13e6c783d94fbf50bf208d4483840003dbb4a807`.
It was pre-registered at execution count zero and executed once with the unchanged
frozen configuration.

| Mode | R@1 | R@3 | R@5 | MRR | nDCG@5 |
|---|---:|---:|---:|---:|---:|
| Lexical | .6667 | .7604 | .7604 | .7392 | .7258 |
| Semantic hybrid | .7500 | .8750 | .9792 | .8325 | .8664 |
| Calibrated reranker | .8854 | .9688 | .9792 | .9274 | .9384 |

Metrics use 96 positive retrieval queries. Absence and isolation each use 8 cases and
scored 1.0. Citation precision/recall and support are `.8854/.9688/.8854`;
unsupported claims are zero. Results fail final acceptance and the fixture is now
consumed.
# Phase 2B hard-negative evaluation

The consumed 120-query fixture was checksum-verified and inspected only; it was
not executed or tuned. Its safe aggregate taxonomy is in
`phase2b-consumed-benchmark-taxonomy.json`.

Development used 127 new queries. The current and BGE-small candidate pairs
tied on quality; the current `all-minilm-l6-v2` plus
`ms-marco-minilm-l-6-v2` pair was retained because it used less peak memory and
had lower steady-state latency. After that decision, a separate 160-query blind
fixture was registered with SHA-256
`47d8e06e4377941ff4e1408f120a7c269ce8c9c15d63ab90cbd65dec5933c54c`
and executed exactly once. See its pre-registration and result JSON files for
category counts, explicit denominators, load time, RSS, latency, and metrics.
