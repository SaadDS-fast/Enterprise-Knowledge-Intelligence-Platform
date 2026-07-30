# Grounded-generation quality evaluation

`grounded-generation-benchmark-v1.json` preregisters 80 development cases and a separate
100-case blind holdout spanning 25 categories. The holdout permits one execution and may
not be used for tuning. It compares deterministic extraction, the untrusted Ollama
candidate, and the final verified/fallback answer.

The fixture is sealed before live execution. Live results remain pending because no
running Ollama service or installed allowlisted model was available at implementation
time. The blind holdout must not be executed until that operator dependency is present;
recording invented metrics would consume the holdout without valid evidence.
