# Validation Report

## Verifiable Answer Passport Phase 1 release gate — 2026-08-01

**Status: PASS.** Validated on `feat/verifiable-answer-passport` from implementation baseline
`7a3e96615e7b31a769bf5d858d27f92c3e001b05`. The phase is limited to the pure cryptographic core,
synthetic-only eligibility/snapshot fixtures and standalone offline verifier.

Implemented artifacts are `vap-1`, detached `application/vap+jws`, `vap-trust-1`, and optional
synthetic `vap-snapshot-1`. PyCA cryptography supplies Ed25519. Canonical JSON and the narrow
RFC 7515 Appendix F standard encoded detached-JWS envelope are custom, tested code; RFC 7797 is
not used. Canonicalization is a restricted RFC 8785-compatible profile, not unrestricted RFC
conformance.

Release evidence:

- 99 focused passport tests passed, including 25 independent-audit additions, 8 canonical golden
  vectors, independent signer/verifier interoperability in both directions, exact JOSE-header
  attacks, compound-failure precedence and every status-to-exit mapping.
- Complete backend: 324 passed, 4 environment-gated skips; 80% total coverage and approximately
  94% passport-package coverage.
- Compileall, Ruff lint/format, passport Mypy, Bandit (zero findings), and pip-audit (no known
  vulnerabilities) passed.
- The required repository-wide Mypy command was executed and exposed 29 pre-existing errors only
  in untouched modules; no passport Mypy errors exist.
- Frontend npm clean install, lint (0 errors/1 pre-existing warning), typecheck, 27 tests, production
  build and production audit (0 vulnerabilities) passed.
- Docker Compose config, backend image build and PostgreSQL Alembic drift check passed; no migration
  is required.
- Module and installed CLI forms passed. Exit `0` is only `VERIFIED`; exit `2` is review-required
  (`VERIFIED_WITHOUT_SNAPSHOT`, `STALE`, `EXPIRED`, `INDETERMINATE`); exit `1` covers every other
  status and input failure. Normal invalidity has no traceback.
- Integrity and trust failures deterministically take precedence over freshness: content changes,
  unknown keys, invalid signatures and snapshot mismatches cannot be softened by expiry/staleness.
- Socket/DNS creation was blocked during successful verification; static dependency tests exclude
  retrieval, generation, embeddings, rerankers, Agent, Research, APIs, persistence and networking.
- Snapshot absence remains `not_supplied`; a valid signature does not claim current factual truth,
  universal correctness, or evidence authorization.
- Secret hygiene found no tracked/intentional private key, PEM, credential or token. The test signer
  is ephemeral and never serialized.
- Support threshold remains `0.72`; Search remains one configured retrieval pass and Agent retry
  budget remains `0`. No holdout was executed or changed.
- No production issuance, endpoint, migration, frontend workflow, AWS/cloud integration, push,
  merge or tag was introduced during validation.

Detailed protocol and limitations are in
`docs/implementation/verifiable-answer-passport-protocol-v1.md`,
`docs/implementation/verifiable-answer-passport-phase-1.md`, and `KNOWN_LIMITATIONS.md`.

Validated on 2026-07-23 on branch `release/v0.2.1-operational-hardening`.

## v0.2.1 Operational Hardening Addendum

**Status: PASS.** Current baseline commit before this release-hardening commit was
`df183cab489c00e4c0a94f6c2b0f1cb60471bf57`; protected tag
`v0.2.0-controlled-agentic-rag` remains there and no `v0.2.1-controlled-agentic-rag`
tag was created during validation.

Current hardening results:

- Backend: `.venv/bin/pytest -vv` passed `117 passed, 2 skipped`; coverage stayed `76%`;
  Ruff check and format check passed; Bandit reported no issues; pip-audit reported no known
  vulnerabilities in audited PyPI packages.
- Frontend: lint passed with one existing Fast Refresh warning, typecheck passed, Vitest passed
  `9 files / 24 tests`, `npm run build` passed on Next.js `16.2.11`, and
  `npm audit --omit=dev` reported 0 vulnerabilities.
- Browser runtime: default Playwright passed `1 passed, 4 skipped`; enabled agentic Playwright
  passed `5 passed` against Dockerized PostgreSQL/Redis/MinIO/Celery.
- Docker/migrations: `docker compose config`, observability profile config, web-search profile
  config, `alembic upgrade head`, and `alembic check` passed.
- Operational outage script: Redis dispatch outage recovered from `dispatch_failed` to completed;
  MinIO export outage recovered with exactly one markdown/PDF/DOCX artifact each and valid DOCX;
  report-worker, ingestion-worker, and backend restarts completed in the real stack; PostgreSQL
  interruption returned a sanitized 500 and health recovered; cancellation ended in
  `CANCELLED`; idempotent research replay returned the same job with valid PDF.
- Tenant isolation matrix: cross-document reference `403`, cross-document error `FORBIDDEN`,
  read research `404`, artifact metadata `404`, artifact download `404`, read agent run `404`.
- External providers: deterministic opt-in returned one citation; live SearXNG opt-in returned
  status 200, `external_access_performed=true`, provider `searxng`, 5 external evidence items,
  and 4 citations.
- Observability: Prometheus ready, backend/ingestion/evaluation/report targets up, agent metric
  families present without forbidden sensitive labels; Grafana API returned the
  `EKIP Agentic Runtime` dashboard; OpenTelemetry collector debug exporter logged one trace batch
  after enabling `OTEL_ENABLED=true`.
- Load probes: 5 users / 15 requests: 100% success, p99 211.8 ms; 10 users / 30 requests:
  100% success, p99 374.8 ms; 20 users / 60 requests: 100% success, p99 851.9 ms.
- Default flags restored after validation: `AGENTIC_RAG_ENABLED=false`,
  `AGENT_RESEARCH_ENABLED=false`, `AGENT_WEB_SEARCH_ENABLED=false`,
  `WEB_SEARCH_PROVIDER=disabled`.

## Environment

- Pre-hardening safety tag: `v0.2.0-rc1-prehardening` at `952f34e65a30c3f60b3db242d60416f1a94119e7`
- Protected release tag: `v0.1.0-enterprise-mvp` unchanged at `469e561d763ac03e6c416f9ac816c8b0873f30da`
- Working tree: final controlled-agentic-RAG hardening changes ready for release commit
- Python: 3.12.13
- Node: v20.20.2
- npm: 10.8.2
- Docker: 29.6.2
- Docker Compose: v5.3.1

## Overall Status

**PASS**

The Dockerized runtime stack passed validation for backend, frontend, PostgreSQL/pgvector, Redis/Celery, MinIO, Prometheus worker scraping, browser E2E, observability config, optional SearXNG health, and local load probes. Ollama has local models installed and was checked without pulling paid or remote dependencies.

Controlled agentic frontend update: this phase adds disabled-by-default Next.js workspaces for controlled agent queries, safe run timelines, asynchronous cited research reports, artifact downloads, and frontend feature-flag plumbing while preserving the existing `/search` endpoint and legacy `/research` route. Backend authorization and feature flags remain authoritative.

## Key Runtime Results

- Completed-task retry: **PASS**. A duplicate Celery task for completed job `b1f52514-8a77-489b-afc7-40a90f6d9ae3` returned successfully, preserved request id `a99f349a-631a-4089-9a44-62093233da46`, and kept counts at 1 chunk / 1 embedded chunk. Targeted logs had no asyncpg or event-loop warnings.
- Redis outage recovery: **PASS**. Upload while Redis was stopped returned 202 with job `54a2de89-f572-4f83-91f3-c8cc22247702` marked `retry_pending`; after Redis restart the backend dispatcher automatically published it and the job completed. Database check showed 0 jobs stuck in `retry_pending` or `dispatch_failed`.
- MinIO outage safety: **PASS**. Upload while MinIO was stopped returned sanitized 500 and document count stayed 0 for that workspace.
- Worker metrics: **PASS**. Prometheus targets for `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103`, and `backend:8000` all reported `up=1`. `ekip_worker_tasks_completed_total{worker_role="ingestion"}` reached 4 after runtime probes.
- Browser E2E: **PASS**. Playwright Chromium ran against Dockerized frontend/backend: 1 spec passed covering register, login, upload, ingestion, search evidence, abstention, tenant isolation, logout, and cleanup.
- Internal agent Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true` for the probe only, uploaded document job `4982e894-bc00-4c54-b069-f79f44f7f71f` completed through Celery/PostgreSQL/Redis/MinIO and `/agent/query` run `20bc2a99-e839-468d-87b6-4d970909f327` returned `SUFFICIENT_EVIDENCE`, 1 evidence item, 1 citation, and `abstained=false`. The stack was restored to the default disabled agent posture afterward.
- Agent metrics: **PASS**. `/metrics` exposed `ekip_agent_runs_started_total`, `ekip_agent_runs_completed_total`, `ekip_agent_runs_failed_total`, `ekip_agent_tool_calls_total`, `ekip_agent_replans_total`, `ekip_agent_fallbacks_total`, `ekip_agent_duration_seconds`, and `ekip_agent_tool_duration_seconds`.
- External-disabled runtime: **PASS**. With agent enabled and external providers disabled, internal run `4b52e7e2-2dd2-46cc-bd89-e0a5c5f16310` answered from internal evidence, and public-disabled run `1db97c59-c459-4765-93ba-a8b03c4cf0ab` abstained with no external access.
- Deterministic external runtime: **PASS**. With `WEB_SEARCH_PROVIDER=deterministic`, public run `e4271e7e-b199-458e-a217-f4064478cdf6` returned external provenance and citation; internal-preference run `01a2870f-5ab1-4086-828c-d710c6a84f3c` did not call external search when internal evidence was sufficient.
- External metrics: **PASS**. `/metrics` exposed `ekip_agent_external_tool_calls_total`, `ekip_agent_external_tool_failures_total`, `ekip_agent_external_tool_duration_seconds`, `ekip_agent_external_sources_used_total`, `ekip_agent_ssrf_blocks_total`, and `ekip_agent_external_timeouts_total`.
- Multi-source evidence metrics: **PASS**. `/metrics` exposes evidence, deduplication, claim, conflict, citation, synthesis-fallback, and context-budget metric families with low-cardinality labels only.
- Multi-source Docker runtime probes: **PASS**. Deterministic no-internet runtime covered internal supported run `30a13d77-efaf-4cd8-99ec-da772fc5fc2b`, public external run `854fac77-0904-4aaf-b156-abd43c8142df`, internal-preferred mixed run `9d7a5e72-f089-4d6b-9ace-54c6f7a0865c`, partial run `c71c9c10-f24e-4b8b-9138-2f43c1820cc0`, internal conflict run `08704576-8908-4635-9095-52f57e3bf4cd`, internal/external conflict run `ef36a0f9-be84-43f0-923a-1ee2b430200b`, knowledge-absence run `e9896f8c-a078-42f4-94f1-b29a6935493b`, ambiguous run `0c6580ce-c538-4140-b1b6-bbf0266ba6b7`, prompt-injection run `1c591745-b41d-448f-8d8b-e3a50064a8ea`, and tenant-isolation run `30a54d73-9b9d-4914-8179-eed436c7a155`. Backend was restored to default disabled-agent/external settings afterward.
- Research report tests: **PASS**. Targeted backend research tests passed: 12 tests covering feature flag denial, lifecycle, exports, signed download tampering, idempotency, knowledge absence, conflicts, cancellation, tenant isolation, workspace document-scope denial, and `/search` regression.
- Research report Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true` and `AGENT_RESEARCH_ENABLED=true` for the probe only, Docker API upload job `1985fb7d-2fd7-488b-994a-fa9bf5b0a9b6` completed through PostgreSQL/Redis/MinIO/Celery, research job `b4653536-ffd1-4132-b513-4bd19680e5dd` completed through `report-worker`, agent run `3593b650-7676-4616-b4fe-9a5d6ad33e5c` returned 1 source and 1 verified citation, and markdown/PDF/DOCX downloads passed. Backend and workers were restored to default disabled agent/research flags afterward.
- Agentic frontend Docker runtime: **PASS**. With `AGENTIC_RAG_ENABLED=true`, `AGENT_RESEARCH_ENABLED=true`, `NEXT_PUBLIC_AGENTIC_RAG_ENABLED=true`, and `NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED=true`, Docker rebuilt backend/frontend images and Playwright passed 2 Chromium specs against the real PostgreSQL/Redis/MinIO/Celery stack. The gated spec covered registration, upload, Celery ingestion, `/agent` query, `/agent/research` job creation, `/search` route visibility, and document cleanup.
- Final hardening Docker runtime: **PASS**. Default-disabled rebuilt stack passed health checks, Alembic drift check, logs review, and default Playwright runtime spec. Enabled deterministic rebuilt stack passed 5 Chromium specs covering runtime search, deep agent workspace, research reports, responsive layouts, and accessibility checks.
- Local load probes: **PASS** under the laptop profile. 5 users/15 requests: 100% success, p50 34.2 ms, p95 123.0 ms, p99 135.7 ms, 21.4 rps. 10 users/30 requests: 100% success, p50 82.4 ms, p95 383.3 ms, p99 387.0 ms, 7.44 rps. 20 users/60 requests: 100% success, p50 169.5 ms, p95 493.6 ms, p99 599.1 ms, 4.79 rps.
- Observability hardening: **PASS**. Prometheus alert rules and Grafana dashboard provisioning render through `docker compose --profile observability config`; Prometheus readiness returned ready and backend `/metrics` exposed all requested agent metric families.
- Optional local profiles: **PASS/PARTIAL**. SearXNG image pulled, started on the internal network only, and `/healthz` returned `OK`; startup logs show expected default-template engine/limiter warnings for live internet engines. Ollama CLI is installed and local models `tinyllama:latest` and `llama3:latest` are available; no model pull was performed.

## Commands Run

- `docker compose config`
- `docker compose --profile web-search config`
- `docker compose build`
- `docker compose build backend`
- `docker compose build frontend`
- `docker compose --profile observability up -d`
- `AGENTIC_RAG_ENABLED=true docker compose --profile observability up -d backend ingestion-worker evaluation-worker report-worker`
- `docker compose run --rm backend alembic check`
- `docker compose --profile observability ps`
- Live Docker agent API probe for upload, Celery ingestion, `/agent/query`, citations, evidence, and metrics
- Live Docker deterministic external provider probes for disabled mode, external-enabled mode, and internal-preference mode
- Prometheus API queries for `up` and worker completion metrics
- Live API probes for upload, retry, Redis outage recovery, and MinIO outage safety
- `backend/.venv/bin/python -m compileall app tests`
- `backend/.venv/bin/ruff check app tests`
- `backend/.venv/bin/ruff format --check app tests`
- `backend/.venv/bin/pytest -vv`
- `backend/.venv/bin/pytest --cov=app --cov-report=term-missing`
- `backend/.venv/bin/bandit -r app`
- `backend/.venv/bin/pip-audit`
- `npm run lint`
- `npm run typecheck`
- `npm run test`
- `npm run test:e2e`
- `E2E_AGENTIC_ENABLED=true npm run test:e2e`
- `npm run build`
- `npm audit --omit=dev`
- Agent targeted tests for state transitions, planner validation, typed tools, query reformulation, retrieval retry, evidence diagnosis, safety review, fallback, scoped denial, prompt injection handling, and `/search` regression
- Research targeted tests for async lifecycle, exports, idempotency, cancellation, scoped denial, conflict/absence report cases, signed downloads, and `/search` regression

## Source Validation

- Deterministic-core targeted validation: **PASS** for structure-aware chunking, direct
  `Topic: Functions` extraction, unrelated heading/value non-conflict, genuine demo-topic
  conflict, normalized evaluation match, and controlled-agent supported answer regressions.
- Backend compile: **PASS**
- Backend Ruff lint/format: **PASS**
- Backend tests: **116 passed, 2 skipped**
- Backend coverage: **76%**
- Bandit: **PASS**, no issues
- pip-audit: **PASS**, no known vulnerabilities for audited PyPI packages
- Frontend lint: **PASS**, 0 errors and 1 existing Fast Refresh warning in `app/layout.tsx`
- Frontend typecheck: **PASS**
- Frontend unit/component tests: **PASS**, 9 files and 24 tests
- Frontend Playwright E2E: **PASS**, 1 default Chromium spec; 5 Chromium specs in gated deterministic agentic Docker mode
- Frontend build: **PASS**
- npm audit: **PASS**, 0 vulnerabilities
- Frontend dependency security: **PASS**, `next@16.2.11` resolves the audited Next.js advisory and `npm audit --omit=dev` reports 0 vulnerabilities
- Controlled agent, external provider, and multi-source evidence targeted tests: **PASS**, 65 passed
- Evidence normalization: **PASS**, internal, SearXNG, Wikipedia, arXiv, and approved API paths tested
- Deduplication: **PASS**, external URL duplicates merge and cross-tenant internal evidence never merges
- Rank fusion: **PASS**, deterministic RRF preserves internal priority for organization-specific questions
- Claim verification: **PASS**, supported, partially supported, unsupported, and conflicted statuses tested
- Conflict detection: **PASS**, numeric, date, and owner/entity contradictions tested
- Citation validation: **PASS**, unknown and unrelated citation labels rejected
- Deterministic synthesis: **PASS**, grounded extractive answer and unsupported-claim removal tested
- Evaluation metrics: **PASS**, fixture execution measured support rate 0.5, citation precision 1.0, citation recall 0.75, unsupported claim rate 0.3333, abstention accuracy 1.0, conflict detection accuracy 1.0, and average evidence count 2.5
- SearXNG adapter: **PASS**, parser tests and optional Compose profile config passed; live SearXNG launch was not required for this zero-internet validation pass
- Wikipedia adapter: **PASS**, mocked response parsing passed
- arXiv adapter: **PASS**, mocked Atom parsing passed with hardened XML parser
- SSRF tests: **PASS**, blocked private IPv4/IPv6, localhost, metadata host, Docker hostname, unsafe schemes, and redirects to private destinations
- External prompt injection: **PASS**, malicious external excerpt forced abstention and cleared citations
- External provenance: **PASS**, external citations retain provider/title/canonical URL/retrieval date/excerpt and remain separate from internal citations
- Existing `/search` regression: **PASS**, `/api/v1/search` still returns answer and retrieval diagnosis payload
- Research report targeted tests: **PASS**, 12 passed
- Research exports: **PASS**, markdown, PDF, and DOCX artifacts are generated through the storage abstraction
- Research citation validation: **PASS**, verified citation counts and citation metadata are persisted in the structured report response
- Migration smoke: **PASS**, disposable SQLite Alembic `upgrade head` reached `d9a1f2c3b4e5` and Docker PostgreSQL `alembic check` reported no new upgrade operations
- Docker smoke: **PASS**, `docker compose config` passed and the existing observability stack remained healthy

## Remaining Follow-Up

- Full Ollama runtime generation was not run; local models were listed only.
- Deep destructive outage testing was limited to previously validated Redis/MinIO paths plus a final report-worker restart probe.
- Several scaffolded enterprise modules remain low coverage, reflected in the 76% backend coverage.
- Agentic mode, research mode, and external access are disabled by default. Live SearXNG launch, live public internet tests, arbitrary browsing, unrestricted external APIs, major frontend agent UX, admin UI, and AWS deployment are future work.

## Phase 2 Validation — 2026-07-28

Overall: **PARTIAL PASS** because an already-provisioned live model was unavailable. No
model was downloaded.

- Backend compileall, Ruff lint/format, full pytest, and 76% coverage passed.
- Provider allowlist, dimensions, batching, normalization, versioning, unavailability,
  reranker timeout/fallback, scope, isolation, recovery, absence, and shared-service
  regressions passed.
- Authorized idempotent re-index passed; indexing version is `2.0`.
- Frontend `npm ci`, lint (0 errors, one existing warning), typecheck, 28 tests, and
  production build passed.
- Playwright: default 1 passed/4 gated skipped; gated deterministic agentic run 5 passed.
- Bandit passed; pip-audit found no known vulnerabilities; `npm audit --omit=dev`
  found 0 vulnerabilities.
- Docker config/build/restart/health and Alembic upgrade/drift checks passed; all affected
  services ended healthy with defaults restored.
- Live model: N/A (`sentence_transformers` absent and no allowlisted cache).
- Deterministic probe: 96 vectors at dimension 384 in 3.25 ms; approximate process peak
  RSS 70.92 MiB. This is not a live semantic benchmark.
- Live Recall@1/3/5, MRR, nDCG@5, citation precision/recall, model load time, and semantic
  latency are N/A. Metric/contract fixtures passed; no quality improvement is claimed.

## Phase 2 live-model completion — 2026-07-28

Overall: **PARTIAL PASS**. The live models, offline execution, re-index integrity,
fallbacks, isolation, browser UI, and regressions passed. Quality is not a full pass:
semantic hybrid improved Recall@5 from 0.9375 to 1.0000, but the raw cross-encoder
reduced Recall@1 from 0.9375 to 0.8125 and MRR from 1.0000 to 0.9375. All four modes
scored 0.0000 on the deliberately absent-revenue case, so abstention calibration remains
required.

- Embedding: `all-minilm-l6-v2` →
  `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, `st-v1`.
- Reranker: `ms-marco-minilm-l-6-v2` →
  `cross-encoder/ms-marco-MiniLM-L-6-v2`, `ce-v1`.
- Packages: sentence-transformers 5.6.1, transformers 5.14.1,
  huggingface-hub 1.25.1, torch 2.13.0.
- Offline cache-only inference passed for both models. No runtime download or remote
  inference endpoint was used.
- Re-index passed with one live 384-dimensional vector per active chunk, zero
  deterministic vectors, zero duplicate ordinals, obsolete metadata detection, tenant
  isolation, selected-document scope, and idempotent-key replay.
- Cold embedding load plus 12-document batch: 4611.192 ms; warm query: 6.574 ms;
  warm document batch: 15.672 ms. Cold reranker plus four candidates: 152.546 ms;
  warm batch: 18.272 ms. Benchmark process peak RSS: about 559.812 MiB.
- Backend: 155 passed, 4 expected skips, 76% coverage; Ruff, compileall, Bandit and
  pip-audit passed. Frontend: 28 tests, lint/typecheck/build passed; npm audit found
  zero vulnerabilities. Default Playwright passed 1 with 5 gates; live-model browser
  passed 1; feature-enabled responsive agent checks passed 3.
- Docker config/build/up/health and Alembic upgrade/check passed. Semantic and reranker
  defaults were restored disabled.

## Phase 2 retrieval calibration — 2026-07-28

Overall: **PARTIAL PASS**. A 60-query development set selected the frozen configuration;
the separate 40-query holdout was executed once and was not used for retuning.

Holdout calibrated reranker: Recall@1/.3/.5 `.9375/.9688/.9688`, MRR `.9570`,
nDCG@5 `.9572`, citation precision/recall `1.0000/.9688`, answer support `.9375`,
unsupported claims `.0000`, absence `1.0000`, recovery `.9688`, and isolation `1.0000`.
Recall@5 missed the `.98` target and answer support missed `.95`; all other targets
passed. Materials deformation ranked first in 9/10 holdout variants, including the
required query. Revenue probes abstained without budget citations.

Frozen weights are lexical `.45`, semantic `.55`, reranker blend `.25`, minimum margin
`.08`, top-N `20`, return-K `8`. Cross-encoder output is blended rather than replacing
fusion; ambiguous/absence intents skip it and low-margin/unavailable calls preserve
fusion. Cold load was 4809.475 ms embedding and 180.344 ms reranker; peak RSS was about
535.406 MiB.

## Final Phase 2 acceptance closure — 2026-07-28

Status: **BLOCKED / PARTIAL PASS** on the new blind quality gate. The frozen calibration
was unchanged. A new 120-query fixture was pre-registered with SHA-256
`16dc10caf8b9608d60abf84f13e6c783d94fbf50bf208d4483840003dbb4a807`,
then executed exactly once. It did not reuse the consumed 40-query holdout.

Calibrated results over 96 positive retrieval queries were Recall@1/3/5
`.8854/.9688/.9792`, MRR `.9274`, nDCG@5 `.9384`, citation precision/recall
`.8854/.9688`, answer support `.8854`, and unsupported claims `.0000`. Eight absence
and eight tenant-isolation cases each scored `1.0000`. Recovery-at-3 was `.9688`
over the same 96 positive queries; 40 were explicitly marked recovery cases.
Elasticity hard negatives ranked first in 6/8 cases.

Operational closure passed: backend tests use unique tenant/workspace identities;
browser documents use exact run-scoped names; a dedicated Compose project used
disposable PostgreSQL, Redis, and MinIO volumes. Default Chromium passed 1 with 5 gates;
feature-enabled Chromium passed 5 with 1 live gate. The full backend suite passed
158/158 with 4 expected skips and 76% coverage. Docker builds, Alembic upgrade/check,
Bandit, pip-audit, and npm audit passed. Disposable containers, network, and volumes
were removed after validation.
# Phase 2B hard-negative remediation (2026-07-29)

Status: PASS on the one-time 160-query blind holdout. The frozen current model
pair achieved Recall@1 0.9250, Recall@3/5 1.0000, MRR 0.9893, nDCG@5 0.9921,
citation precision 0.9786, citation recall and answer support 1.0000,
unsupported claims 0, knowledge absence/recovery/tenant isolation 1.0000, and
hard-negative Recall@1 1.0000. Denominators were 160 total, 140 positive, 20
hard-negative, 15 absence/isolation, 5 ambiguous, and 5 selected-document.
Fixture SHA-256: `47d8e06e4377941ff4e1408f120a7c269ce8c9c15d63ab90cbd65dec5933c54c`.
It was executed exactly once.

The isolated Chromium acceptance exercised all 15 requested outcomes and
passed. The Docker acceptance used project `ekip_phase2b`, so PostgreSQL,
Redis, MinIO, documents, tenant/workspace state, and its network were
independent of normal services; all project containers, volumes, and the
network were removed after validation.

# Phase 2B closure

Status: PASS. The remaining broad-agentic regression closes with a verified,
disposable current-source runtime. Default Playwright passed 1 with 6
intentional skips; agentic Playwright passed 5 with 2 intentional skips,
including all three responsive checks; the isolated 15-case profile passed.
Runtime preflight rejected mismatched identities/flags before test execution.
No genuine product regression reproduced.

The 160-query fixture was not rerun or modified. Its SHA-256 remains
`47d8e06e4377941ff4e1408f120a7c269ce8c9c15d63ab90cbd65dec5933c54c`;
models, calibration, thresholds, and recorded metrics remain frozen.

# Pre-Ollama response-state validation

The deterministic invariant and normalization matrix passes. It covers supported
facts, equivalent wording, currency/unit equivalence, true value and role
conflicts, current-versus-superseded resolution, revenue/budget separation,
knowledge absence, retrieval failure, composite completeness, selected scope,
fallback consistency, and cancelled-answer rejection. Existing Search, Agent,
Evaluation, Research, authorization, isolation, injection, SSRF, parser, CSP, and
model-allowlist regressions provide system-level evidence.

Consumed Phase 2 and Phase 2B blind benchmarks were neither executed nor modified.
# Ollama grounded-generation validation (2026-07-30)

Status: PARTIAL PASS. Static/unit validation passes for endpoint restrictions, structured
schema, reasoning exclusion, evidence-ID authorization, numeric/negation/equation drift,
server-side citations, fallback, and circuit recovery. Live Ollama, the sealed holdout,
and live browser acceptance are not executed because the installed Ollama 0.22.1 client
cannot connect to a service and no installed model inventory is available. The blind
holdout remains sealed rather than fabricating or tuning against results.

The default isolated Docker/Chromium acceptance passed against disposable PostgreSQL,
Redis, and MinIO volumes. The harness removed its containers, network, volumes, traces,
screenshots, and reports. A first non-isolated browser attempt hit the pre-existing stale
runtime and was discarded; the isolated rerun passed.

## Live Ollama closure — 2026-07-31

Status: PARTIAL PASS. Local Ollama `0.32.1` and `llama3:latest`
(`365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`,
8.0B, Q4_0, context 8192) were ready. The 100-case holdout was executed once.
Safety, citations, isolation, deterministic states, injection resistance, and fallback
passed; completeness, claim recall, numeric, entity/role/date, and equation gates failed.
Docker-to-host Ollama and isolated Chromium passed through `host.docker.internal`.
An unavailable local port produced sanitized extractive fallback, the circuit opened at
the configured threshold, and verified live generation recovered after the recovery
window. Normal persistent Compose services and volumes remained running.

## Grounded generation v2

The new development benchmark passed 120/120 cases. The sealed 140-case holdout
(`4eb23dcd23e734ee43e155fa077c451a40d195ee2d1bcfd5c198285f8aba1c7d`) was
executed exactly once and is consumed at `1/1`. It passed 152/152 claims, 144/144
citations, 140/140 final answers, every typed-fact and isolation category, and 4/4
claim-completion checks. Of 132 live attempts, 124 returned candidates and all 124
were schema-valid and verified; eight unavailable/circuit cases used complete safe
fallback. Average/p50/p95 latency was 4177.93/3627.47/8879.99 ms with 21,894 input
and 13,944 output tokens.

Live isolated Chromium is a PARTIAL PASS. Monetary, currency, frequency,
percentage, role, effective/published date, and subsequent safe rendering checks
executed through the current Docker build. Search's canonical integration rejected
the exact equation fail-closed, and a correct negation answer lacked a validated UI
citation; a later owner/date multi-claim case was classified as insufficient evidence
before generation. These integration gaps were not used to retune or rerun the
consumed holdout. Default Chromium passed 1/1 and agentic Chromium passed 5/5.

## Search/browser acceptance closure — 2026-07-31

Status: **PASS**. The quadratic definition was falsely classified as conflicting
because a coarse multi-chunk negation heuristic interpreted “a is not zero” as a
contradiction. Typed conflict assessment is now authoritative, preserving
`ax² + bx + c = 0` and its non-zero condition. Negative obligations are now typed
before one-term ambiguity handling, so the supported claim retains its authorized
citation through API serialization and UI rendering. Owner/effective-date requests
now produce separate typed components; equivalent nested owner facts are deduplicated,
and complete single-source multi-claim evidence no longer inherits the distinct-source
rule that remains mandatory for comparisons.

Fresh isolated live-Ollama Chromium passed 1/1, covering seven strict Search cases,
malformed-candidate fallback, selected-document scope, Tenant B isolation, and
desktop/tablet/mobile layouts without console errors, raw JSON, internal paths, stale
documents, or overflow. Default Chromium passed 1 with 7 gated skips; agentic Chromium
passed 5 with 3 gated skips. Backend passed 215 with 4 environment-gated skips at 78%
coverage; frontend passed 34/34 tests and its production build. Docker builds and
Alembic upgrade/check passed in disposable profiles. Both consumed holdouts were
neither executed nor modified.

# Enterprise end-to-end release hardening (2026-07-31)

Candidate: `v0.3.0-enterprise-rc1` (proposed only). Baseline and rollback commit:
`736a402`. The versioned corpus contains 100 synthetic documents across ten departments,
ten supported formats, and three isolated tenants. The explicit acceptance matrix contains
118 cases. The disposable current-source profile accepted 100/100 uploads, completed
100 ingestions without a failure, timeout, or stuck record, ran 30/30 canonical Search probes,
passed authorized/cross-tenant selected-document checks, idempotent reprocess, responsive
Chromium, current-source Docker builds, and Alembic upgrade/check. Final load, soak,
regression, operational, and scanner totals are recorded in `TEST_RESULTS.md`.

The grounded-generation v1/v2 benchmarks were not run. Their fixtures, locks, and
historical results remain immutable. No cloud or AWS readiness is claimed.

Status: **PARTIAL PASS**. The 20-minute soak, concurrency run, backup/restore,
downgrade/upgrade, MinIO privacy check, and enterprise browser passed. A first operational
failure-injection run exposed that the validation script omitted the isolated Compose
override during MinIO recovery; the harness was corrected. The platform execution quota
then rejected the authoritative rerun and all further privileged Docker/Git operations
until 2026-08-05 12:43 PKT, so current-source live Ollama/default/agentic reruns and the
requested commit could not be completed in this session. No product security, isolation,
data-integrity, or unsupported-claim failure was observed.

## Authoritative closure rerun (2026-08-01)

The quota-blocked profiles were rerun from current source. Final Search passed 30/30
(24 `SUPPORTED`, 6 safe `INSUFFICIENT_EVIDENCE`), including authorized selected-document
200 and cross-tenant 404 behavior. Default Playwright passed its enabled scenario with
eight accurate feature-gated skips. Agentic/Research/accessibility passed five enabled
scenarios across desktop, tablet, and mobile with four unrelated skips. Live Ollama passed
against Ollama 0.32.1 and the required `llama3:latest` digest.

The corrected operational probe passed PostgreSQL, Redis, MinIO, backend, ingestion-worker,
and report-worker interruption/recovery, idempotency, tenant isolation, sanitized failure,
request-ID presence, and metric-label privacy checks. Enterprise Chromium, backup/restore,
the reversible migration cycle, and Alembic check passed.

Status remains **PARTIAL PASS** because the freshly rerun provisioned-model semantic and
semantic-plus-reranker benchmark failed release acceptance: both modes reported unsupported
claim rate `0.2222` and knowledge-absence accuracy `0.0`; the reranker also placed one
materials hard positive at rank 2. No retrieval retuning was performed. Per the release
gate, no hardening commit, push, merge, or tag was created.

## Semantic and release closure — 2026-08-01

Status: **PASS**. The earlier result remains above as historical before-remediation data.
Primary failure taxonomy was: incorrect evidence-sufficiency interpretation 1, incorrect
absence classification 1, and reranker ordering/evaluator blend error 1. All other requested
categories were 0: nearest-neighbour, stale index, model/alias, dimension, normalization,
scope filter, obsolete version, duplicate dominance, semantic weighting, fusion
normalization, fixture expectation, hard-negative confusion, and incomplete retrieval.

After the general evaluator corrections, semantic hybrid passed 8/8 positive cases plus
1/1 absence and semantic-plus-reranker passed the same 9/9 safety cases. Both reported
unsupported-claim rate 0, absence accuracy 1.0000, citation precision/recall 1.0000,
Recall@5 1.0000, selected-document isolation 1.0000, and tenant isolation 1.0000. The
materials hard positive moved from rank 2 to rank 1 under the single frozen blend. Models
were fully loaded with the required aliases and 384-dimensional embedding; no fallback was
used. Frozen lexical `.45`, semantic `.55`, reranker `.25`, margin `.08`, top-N `20`, and
return-K `8` remain unchanged.

The live operational probe covered login success/failure, upload, reprocess, Search,
selected-document Search, Agent, Research, role denial, cross-tenant denial, and delete.
Response/audit request-ID correlation passed, actor and workspace scope were present, and
the private-payload scan found zero prohibited fields. Backend passed 221 tests with 4
environment-gated skips and 78% coverage. Frontend passed 34 tests, typecheck/build, and
lint with zero errors and one inherited warning. Default, agentic/accessibility, enterprise,
and live-Ollama Chromium profiles passed. Docker builds, Alembic, Bandit, pip-audit, and
npm production audit passed.

## Thesis-isolated grounding assurance (2026-08-01)

Status: **PARTIAL PASS**. The architecture audit found legacy post-insufficiency retrieval
and technical UI exposure. The working changes enforce one Search/Agent document retrieval
pass, set the compatible Agent retry budget to zero, use a neutral refusal, and remove
technical retrieval details from Search UI presentation.

The new 300-document fictional corpus and 1,350-case registry were frozen as 450 development
and 900 blind cases. The blind holdout checksum is
`d090a6e007de9c385ca0b5563e716f5382bb1e5e09051ad46cdd66baa3d50f5a` and execution is
consumed at 1/1. A frozen split-order defect put zero answer/conflict cases in the blind
partition. Its 900 refusal cases passed, but claim/citation/conflict metrics are vacuous.
The mandatory gate is therefore not satisfied; the holdout was not altered or rerun and no
commit was created.

## Grounding Assurance v2 closure (2026-08-01)

Status: **PASS**. V1 remains unchanged and refusal-only at checksum
`d090a6e007de9c385ca0b5563e716f5382bb1e5e09051ad46cdd66baa3d50f5a`, execution 1/1.
Independent v2 passed group-stratified preflight and its single blind execution at checksum
`4515b533b96cfc907aeb08721ff05df21654d211466116ad59c43638565f32aa`.

V2 blind results were 360/360 supported decisions, 405/405 neutral refusals, and 135/135
conflict disclosures. All mandatory accuracy/integrity rates were 1.0000 and every leakage,
unsupported, adaptive, reformulation, and Top-K-change count was zero. Threshold `0.72` was
unchanged. Backend passed 225 tests with 4 environment-gated skips and 79% coverage. Default
Chromium passed 1/1; Agent/Research/accessibility passed 5/5; live Ollama passed 1/1; live
lexical/semantic/reranker checks passed. Docker builds and Alembic checks passed in isolated
profiles. Bandit, pip-audit, and npm production audit passed.
