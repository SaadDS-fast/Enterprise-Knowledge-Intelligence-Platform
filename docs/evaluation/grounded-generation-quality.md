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
