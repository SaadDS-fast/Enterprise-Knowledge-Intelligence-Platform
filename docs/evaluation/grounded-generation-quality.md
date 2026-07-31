# Grounded-generation quality evaluation

`grounded-generation-benchmark-v1.json` preregisters 80 development cases and a separate
100-case blind holdout spanning 25 categories. The holdout permits one execution and may
not be used for tuning. It compares deterministic extraction, the untrusted Ollama
candidate, and the final verified/fallback answer.

The fixture is sealed before live execution. Live results remain pending because no
running Ollama service or installed allowlisted model was available at implementation
time. The blind holdout must not be executed until that operator dependency is present;
recording invented metrics would consume the holdout without valid evidence.

## Live results

The prior pending status is closed. Development ran 80 cases, configuration was frozen,
and the checksum-locked 100-case holdout ran exactly once (`1/1`). Holdout results:
claim precision 1.0000, claim recall 0.7375, citation precision/recall 1.0000,
answer support 0.7375, unsupported claims 0.0000, numeric accuracy 0.7500,
entity/role/date accuracy 0.9167, equation preservation 0.8750, schema-valid
0.9875, verification-pass 0.8125, fallback success 1.0000, prompt-injection
resistance 1.0000, and completeness 0.7900.

Average/p50/p95 eligible-generation latency was 3118.86/2935.15/4287.17 ms.
The benchmark recorded 11,844 input and 5,236 output tokens; the first measured load
component was 190.26 ms after the operator's earlier cold smoke test (5.13 seconds).
Ollama reported a loaded model size of approximately 5.0 GB on Apple GPU.
Detailed denominators are in `grounded-generation-holdout-results.json`. Result:
PARTIAL PASS; the failed gates are retained without post-holdout tuning.

## V2 remediation result

Safe v1 aggregates classify 21 incomplete answers, including four numeric/unit
misses, one combined entity/role/date miss, one equation miss, and one schema miss;
unsupported-claim and citation failures were zero. Raw v1 outputs were not retained,
so finer overlapping buckets (currency versus frequency, person versus role versus
date, truncation versus omission) cannot be attributed honestly.

The v2 development set contains 120 unique queries. After it passed, configuration was
frozen and a text-distinct 140-query holdout was sealed with fixture checksum
`4eb23dcd23e734ee43e155fa077c451a40d195ee2d1bcfd5c198285f8aba1c7d`
and generator checksum `827006bc757cb1830f6c845fc507d3129968f9862e84984fdd5a86a1a25fe69f`.
The holdout ran once (`1/1`) and is consumed. Denominators are 140 cases, 152 claims,
144 citations, 132 live attempts, 124 returned candidates, 124 schema-valid and
verified candidates, 170 typed facts, four repair cases, and 16 total fallbacks
(eight intentional, eight provider/circuit).

All quality, typed-fact, comparison/composite, injection, isolation, absence,
retrieval-failure, repair, completion, and fallback rates were 1.0000; unsupported
claims were 0.0000. Average/p50/p95 latency was
4177.93/3627.47/8879.99 ms and token usage was 21,894 input / 13,944 output.
Ollama reported a 5.0 GB loaded GPU footprint; process peak RSS was not available.

## Post-holdout Search/browser acceptance

No benchmark was rerun and no historical metric changed. Fresh synthetic documents in
disposable tenants closed three integration-only gaps: quadratic definitions retain the
equation and non-zero condition; negative obligations retain claim-linked citations; and
one authorized source can satisfy separate owner and effective-date components. The
isolated live-Ollama Chromium profile passed its single comprehensive test, including
seven strict answer/citation cases, malformed-candidate fallback, selected scope, Tenant
B isolation, and desktop/tablet/mobile rendering. Prompt, schema, verifier, plan,
registry, evidence-packet, model, and retrieval calibration versions remain frozen.
