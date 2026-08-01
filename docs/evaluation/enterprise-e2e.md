# Enterprise end-to-end release evaluation

The `enterprise-corpus-v1` manifest describes 100 entirely fictional documents across ten
departments and ten supported formats. Runtime files are deterministically materialized by
`scripts/enterprise_corpus.py`; binary files and object-store data are not committed. The
corpus manifest checksum is
`9d3379e09369f6ded46a6d4afe624ad035361e8a15d44956d0f901fde80d138e`.

`enterprise-acceptance-v1` contains 118 explicit contracts with tenant, workspace, role,
documents, flags, action, HTTP/state, claim/citation, fallback, and security expectations.
Its checksum is `70622ae75b25244f1c538bf1e36e9e1263d91b41815b87bc10f74924d8680aa3`.

Run `./scripts/run_isolated_e2e.sh enterprise`. The profile builds current source,
preflights runtime identity, creates private PostgreSQL/Redis/MinIO volumes, ingests all
documents, validates scoped Search and idempotent reprocess, runs bounded load and clean
Chromium, then deletes the project and browser artifacts. The consumed Ollama holdouts are
not inputs to this suite and must not be executed.

## 2026-08-01 closure result

Search, default browser, Agentic/Research/accessibility, live Ollama, enterprise browser,
backup/restore, migration, outage/recovery, observability, security scanners, and core
regressions passed. The independent provisioned-model semantic benchmark did not pass:
semantic and reranker modes each produced unsupported rate `0.2222` and absence accuracy
`0.0`. Status is therefore **PARTIAL PASS** and no release commit or tag was created.

The grounded-generation v1 and v2 holdouts remained at `1/1` and were not executed.
Results above are newly rerun; the 20-minute soak and historical Ollama benchmarks are
preserved prior results. No AWS or cloud-capacity validation is claimed.

## 2026-08-01 semantic remediation result

The prior partial result is retained above. A general evaluator correction now requires
fact-anchor/component coverage instead of treating semantic similarity as factual support,
and applies the frozen reranker blend exactly once. Semantic and reranker modes each passed
8/8 positive cases and 1/1 absence case with unsupported rate 0, absence accuracy 1.0000,
citation precision/recall 1.0000, and isolation 1.0000. The unique materials hard positive
ranks first. No threshold, expected label, production authorization boundary, or consumed
holdout changed. Overall release-hardening evaluation status is **PASS**.
