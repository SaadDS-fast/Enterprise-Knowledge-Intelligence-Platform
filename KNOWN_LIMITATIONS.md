# Known Limitations

## Verifiable Answer Passport Phase 1 limitations (2026-08-01)

- Phase 1 is a cryptographic core and standalone verifier. It is not integrated with production
  answers, APIs, persistence, frontend workflows, deployment, AWS or any cloud signer.
- The synthetic issuer exists only to make eligibility rejection testable. Every issuance fixture
  is synthetic; no application retrieval or generation result is passed to it.
- Canonicalization is a custom, restricted RFC 8785-compatible profile for the tested JSON domain.
  Fractional/exponent numbers and non-finite values are rejected rather than serialized.
- The custom JWS implementation is deliberately not a general JOSE stack. It supports only EdDSA,
  an exact protected `alg`/`kid`/`typ` header, canonical protected-header JSON and RFC 7515
  Appendix F standard encoded detached payloads. RFC 7797, `crit`, `b64`, `cty`, unprotected
  headers, algorithm negotiation, remote key discovery, embedded JWKs and X.509 chains are
  rejected. Replacing it with a library requires equivalent exact-policy, canonical-byte,
  detached-payload and status/precedence behavior plus the independent interoperability matrix.
- `vap-snapshot-1` validates an explicitly supplied synthetic authorized snapshot. Phase 1 does not
  export, authorize, encrypt, transmit or retain production evidence.
- The caller-supplied `vap-trust-1` bundle is the explicit local trust anchor. Root signing and
  distribution, KMS/HSM integration and production key ceremonies remain future work.
- Offline revocation/freshness knowledge is only as current as the supplied trust bundle and
  verifier clock. No hidden network refresh occurs.
- Signature integrity proves that protected bytes validate under the selected trusted public key;
  it does not prove current factual truth, universal correctness or viewer authorization.
- Without a snapshot, evidence content is not independently validated and is reported as
  `not_supplied`, not as valid.
- Repository-wide Mypy currently reports 29 pre-existing errors in untouched modules. The complete
  `app/passport` package passes the configured strict Mypy check.
- GroundSeal Passport is a provisional product name and has not been trademark-cleared.
- No diagnosis, retry, reformulation, recovery or other thesis-reserved behavior exists in the
  passport package.

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
# Phase 2B limitations

The consumed Phase 2 benchmark retained only aggregate stage results, so
per-query attribution among retrieval, reranking, sufficiency, citation
selection, and answer mapping is not recoverable without an impermissible
rerun. The safe aggregate taxonomy records two top-five candidate misses and
nine additional top-one misses. The larger L12 reranker was allowlisted but its
operator-cache provisioning did not complete; no comparison claim is made for
it. Synthetic results do not replace evaluation on an organization's own
terminology and documents.

The original broad-agentic failure run predated runtime identity endpoints, so
the exact Git commits of the unidentified processes on ports 3000/8000 cannot
be reconstructed. Their behavior proves the frontend feature mismatch, and the
same runtime test passes against current isolated source, but it would be
incorrect to assign an unverified historical commit or claim stale documents
were present.

# Response-state limitations

Claim normalization is deterministic and intentionally bounded. Unrecognized
domain phrasing can remain insufficient rather than being guessed, and complex
definition or scope contradictions may need domain-specific normalizers.
Composite support is limited by components extracted from focused citation spans.
Confidence bands are explainable categories, not calibrated probabilities.

The compatibility API still exposes legacy outcome fields, but they are derived
from the canonical state and cannot override it. Removal requires a versioned API
migration. Grounded natural-language generation remains a future Ollama phase and
is not included here.
# Ollama grounded-generation limitations

Live generation requires an operator-started Ollama service and explicitly provisioned,
allowlisted model. This repository never downloads a model. The deterministic verifier is
intentionally conservative and may fall back on valid paraphrases when lexical support is
unclear. Live latency, memory, generation quality, and the one-run blind holdout remain
unmeasured until the local runtime dependency is available.

Live measurements are now available, but `llama3:latest` did not meet the preregistered
answer-quality gates. The sealed holdout is consumed and cannot be used for retuning.
Observed weaknesses are omission of requested qualifiers/units and incomplete supported
claims. Safety remained fail-closed, but a future phase requires a new development set
and independently preregistered holdout before claiming acceptance.

Grounded-generation v2 now meets the new acceptance gates, but local inference remains
operator-provisioned and can be unavailable or open its circuit breaker. Those cases
intentionally use deterministic extractive fallback. The 5.0 GB loaded model footprint
is an Ollama-reported practical measurement, not process peak RSS. The v1 and v2
holdouts are both consumed and must never be rerun or used for tuning.

The previously recorded Search/browser equation, negation-citation, and single-source
owner/date gaps are closed. The verifier remains intentionally conservative for novel
equation forms, obligation phrasing, and compound questions outside the tested typed
patterns; uncertain cases continue to fail closed. True comparisons still require
distinct-source support. Both sealed holdouts are consumed and cannot be rerun or used
for tuning.

# Enterprise release-candidate limitations

The corpus is synthetic and local; results do not establish cloud readiness or production
capacity. Optional local semantic models and Ollama depend on operator-provisioned model
files and workstation resources. Latency and resource measurements characterize only the
validated host. Failure injection is bounded and cannot prove recovery from every storage,
kernel, power, or network fault. Browser accessibility checks cover repository tooling and
responsive keyboard semantics, not a third-party certification audit.

The 2026-08-01 provisioned-model closure rerun did not satisfy semantic release acceptance.
Both semantic hybrid and semantic-plus-reranker produced a `0.2222` unsupported-claim rate
and failed the knowledge-absence case; the reranker also demoted one materials hard positive
to rank 2. The consumed holdouts were not reused and retrieval was not retuned.

That result is retained as historical before-remediation evidence. The later 2026-08-01
closure passed after correcting the evaluation harness's factual-support classification and
single-blend reranker ordering; no frozen production calibration changed. Remaining limits
are environmental: the synthetic local corpus is not a production-capacity claim, optional
models remain operator-provisioned, and accessibility is not third-party certification.

The first grounding-assurance blind holdout is consumed but not release-qualifying. Its
frozen ordered split contains only refusal cases, so it demonstrates fail-closed refusal
behavior but cannot measure supported-answer, citation, or conflict correctness. A future
independently versioned holdout would be required; this consumed fixture must not be rerun.

Grounding Assurance v2 supplies that independent, family-isolated benchmark and passed its
single frozen execution. This demonstrates the defined synthetic benchmark and fail-closed
architecture, not universal correctness or production-capacity performance. The generated
150-case sheet is only prepared for human review; no manual review completion is claimed.
