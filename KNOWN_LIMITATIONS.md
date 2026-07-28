# Known Limitations

Updated on 2026-07-23 from branch `release/v0.2.1-operational-hardening`.

## Implemented And Runtime-Tested

- Dockerized PostgreSQL/pgvector, Redis, MinIO, backend, frontend, ingestion worker, evaluation worker, report worker, Prometheus, Grafana, and OpenTelemetry collector.
- PostgreSQL Alembic drift check against the Docker database.
- Celery ingestion with idempotent completed-task retry.
- Redis outage handling with automatic retry-pending dispatch recovery.
- MinIO outage handling with sanitized error response and no persisted document row.
- Prometheus scraping of backend and worker metrics endpoints.
- Browser E2E for auth, upload, ingestion, search, evidence display, abstention, tenant isolation, logout, and cleanup.
- Bandit, pip-audit, npm audit, backend tests, frontend tests, typecheck, lint, and production build.
- Controlled internal-document agent with disabled-by-default API, deterministic planner, typed internal tools, retrieval retry, evidence diagnosis, citation-aware synthesis, safety review, budgets, safe persistence, audit events, and fallback to adaptive RAG.
- Optional approved external-source tools for disabled, deterministic, SearXNG, Wikipedia, and arXiv providers, gated by request opt-in and disabled-by-default feature flags.
- SSRF/outbound validation for approved provider calls and prompt-injection scanning for external excerpts.
- Unified multi-source evidence normalization, scoped deduplication, deterministic rank fusion, context-budget management, claim-level verification, conflict detection, citation validation, deterministic grounded synthesis, and evaluation metric aggregation.
- Disabled-by-default asynchronous cited research reports using the existing controlled agent, report worker queue, PostgreSQL/Redis/Celery, MinIO-compatible storage abstraction, scoped idempotency, cancellation, signed artifact downloads, and markdown/PDF/DOCX exports.
- Disabled-by-default frontend workspaces for controlled agent queries, safe run timelines,
  asynchronous research submission, report polling/cancellation, artifact downloads, and gated
  Docker browser validation.
- v0.2.1 operational validation for Redis dispatch outage recovery, MinIO export outage recovery,
  backend/report-worker/ingestion-worker restarts, PostgreSQL interruption recovery, cancellation,
  idempotency replay, tenant-isolation denial matrix, Prometheus/Grafana/OpenTelemetry APIs, and
  live SearXNG explicit opt-in search through `/agent/query`.

## Remaining Limitations

- Ollama model generation was not run; local models were listed only.
- Existing documents ingested before the deterministic structure-aware chunking update do not
  automatically receive the new heading/value boundaries or section metadata. Re-upload or
  reprocess those documents before comparing old and new retrieval behavior.
- Practice-question topic discovery depends on explicit headings such as Section, Topic, Chapter,
  Unit, or Subject. If a PDF extractor mangles equations or merges question text without reliable
  headings, deterministic Search abstains instead of fabricating inferred topics.
- Load testing was limited to local 5/10/20-user probes and should not be extrapolated to enterprise traffic.
- Deep destructive outage testing was limited to local Compose service interruption/restart probes;
  host crashes, disk exhaustion, network partitions, and multi-node failover were not tested.
- Grafana dashboard provisioning, Prometheus targets, and OpenTelemetry collector trace export were
  API/log validated; alert firing and long-term trace retention were not tested.
- Several scaffolded modules remain low coverage, including cache, document lifecycle/retention, SSRF, egress policy, audit persistence, and redaction paths.
- Validation data from throwaway runtime probes remains in the Docker database except for documents explicitly cleaned by the Playwright test.
- Agentic RAG and agentic research are still disabled by default and require explicit backend and
  frontend feature flags.
- External-source tools are not enabled by default. Deterministic and live SearXNG opt-in paths were
  runtime-validated locally, but live public internet engine quality remains environment-dependent.
- Optional Ollama claim verification/synthesis interfaces are documented as a future path; this phase uses deterministic verification and synthesis by default.
- Arbitrary browsing, user-supplied URLs, direct SQL tools, shell tools, unrestricted external APIs, admin UI, AWS deployment, and autonomous unrestricted agents are intentionally not implemented.

## Notes

- The Redis outage test intentionally produced broker reconnect warnings in worker logs; workers recovered and processed the retry-pending job.
- The MinIO outage test intentionally produced backend storage exception logs; the API response stayed sanitized and no document row persisted.
- Agent persistence stores operational summaries only; private chain-of-thought storage is intentionally excluded.
# Document extraction OCR

Image-only/scanned PDFs are detected and marked `REQUIRES_OCR`; this phase intentionally does
not include a heavyweight OCR engine. Such documents are not indexed and cannot be answered
from until an authorized OCR-capable future pipeline reprocesses them. See
`docs/implementation/document-extraction-chunking-v3.md`.

## Phase 2 limitations

- Live semantic quality and cross-encoder performance were not measured because no
  operator-provisioned package/model cache was present. Ranked comparison metrics remain
  N/A instead of an unverified improvement claim.
- The pgvector schema is fixed at 384 dimensions. Only compatible aliases are allowlisted;
  another dimension requires a schema/index migration and complete re-index.
- Models are optional and disabled by default. Operators must provision weights outside
  Git, enable aliases, restart affected services, and re-index documents.
- Candidate text is currently loaded after strict SQL scope and then scored in-process.
  A future scale phase should push approximate lexical/vector candidate generation into
  PostgreSQL.
- Live model load time and memory remain unmeasured. The deterministic fallback probe is
  not representative of sentence-transformer resource use.
- Next is evidence/conflict calibration; Ollama is a later separate phase and was not
  used here.

### Live findings

- Live measurements supersede the earlier “unmeasured” note: embedding cold load plus
  corpus batch was 4611.192 ms, reranker cold load plus four candidates was 152.546 ms,
  and benchmark peak RSS was approximately 559.812 MiB on the validation host.
- The raw `ms-marco-minilm-l-6-v2` cross-encoder reduced Recall@1 to .8125 and MRR to
  .9375 versus .9375/1.0000 for live semantic fusion. It confused the composite-wire
  deformation query with a physics displacement item. Production enablement needs
  domain calibration or a guarded blending policy.
- Knowledge-absence accuracy was 0 on the one absent-revenue query in every mode.
  Evidence sufficiency/abstention thresholds require calibration on a larger absence
  set before quality can be declared complete.
- The corpus is intentionally small (14 documents, 9 queries); the latency and memory
  figures are validation-host observations, not capacity guarantees.

## Calibration holdout limitations

- The expanded 40-query holdout reached Recall@5 `.9688` rather than `.98` and answer
  support `.9375` rather than `.95`; Phase 2 therefore remains partial.
- One terminology-light materials prompt and one terminology-light physics prompt still
  miss rank one. Future work should add development examples and deterministic
  question-number/title anchors, then evaluate on a new holdout rather than retuning the
  consumed set.
- The synthetic benchmark contains 12 documents and 100 queries. It is broader than the
  live smoke corpus but is not a substitute for an approved domain-specific evaluation.

## Blind acceptance blocker

The new 120-query blind holdout failed final quality acceptance without calibration
changes: Recall@1 `.8854`, nDCG@5 `.9384`, citation precision `.8854`, and answer support
`.8854` remain below targets. Recall@5 was `.9792`, narrowly below `.98`. Only 6/8
elasticity hard negatives ranked first. The fixture is consumed and must not be used for
tuning; further work requires development-only changes followed by another newly
pre-registered holdout.
