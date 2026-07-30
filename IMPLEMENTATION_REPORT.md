# Implementation Report

Updated on 2026-07-23.

## Branch And Commit

- Current branch: `feature/controlled-agentic-rag`
- Started from agent foundation commit: `14be684`
- Release tag: `v0.1.0-enterprise-mvp`
- Commit status: final hardening ready for release commit.
- Pre-hardening safety tag: `v0.2.0-rc1-prehardening`.

## Agentic Frontend Workspace

Completed in this phase:

- Added disabled-by-default `/agent` workspace for controlled document-grounded agent queries.
- Added `/agent/runs/[runId]` run detail view that displays safe step summaries, tool names,
  statuses, durations, and sanitized errors without hidden reasoning.
- Added disabled-by-default `/agent/research` asynchronous report workspace and
  `/agent/research/[jobId]` job detail view for polling, cancellation, artifact listing, and
  authenticated downloads.
- Preserved the existing `/search` endpoint and frontend route.
- Preserved the legacy `/research` route by keeping its synchronous workflow separate from the
  new agentic report workspace.
- Added typed frontend models for agent outcomes, citations, internal/external evidence,
  conflicts, claims, run timelines, research jobs, and artifacts.
- Added safe external URL rendering and expired signed-artifact URL refresh without persisting
  signed URLs.
- Added frontend feature flags and Docker build/runtime plumbing for agentic RAG, agentic
  research, external-source visibility, and polling interval.
- Added component tests for internal-only agent submission, safe citations, async research
  submission, and expired artifact download refresh.
- Added gated Playwright coverage for registration, upload, agent query, async research creation,
  `/search` route visibility, and cleanup through the real Docker stack.

## Controlled Agentic Research Reports

Completed in this phase:

- Added disabled-by-default `POST /api/v1/agent/research` with feature flag `AGENT_RESEARCH_ENABLED`.
- Added scoped list/read/cancel/artifact/download endpoints under `/api/v1/agent/research`.
- Added a typed research request/response schema, structured report schema, report format enum, signed download token helpers, and deterministic state machine.
- Reused the existing controlled agent, hybrid retriever, reranker, retrieval retry, evidence diagnosis, citations, abstention, claim verification, conflict detection, and safety review paths.
- Added scoped idempotency for tenant, workspace, user, request key, question, document scope, formats, and source policy.
- Added `research_artifacts` persistence and extended `research_jobs` for tenant scope, agent run linkage, state/progress, artifact refs, source/citation counts, cancellation, errors, and pipeline version.
- Added a Celery `ekip.research_report` task for the existing `report-worker` queue and dispatcher recovery for failed research dispatches.
- Added markdown, PDF, and DOCX exports through the existing object-storage abstraction with tenant/workspace/job-scoped object keys.
- Added short-lived signed download parameters for artifact links.
- Added Prometheus metrics for research job starts/completions/failures/cancellations, stage and total duration, sources used, claims/citations validated, exports, export failures, and dispatch retries without sensitive labels.
- Added tests for feature flag denial, report lifecycle, export downloads, signed URL tampering, idempotency, knowledge absence, conflicting evidence, cancellation, cross-tenant denial, cross-workspace document-scope denial, existing `/search` regression, state transitions, scoped object keys, renderers, and token signatures.

## Controlled Agentic RAG

Completed in this phase:

- Added a unified Pydantic evidence model for `internal_document`, `web_search`, `wikipedia`, `arxiv`, and `approved_api` sources.
- Added normalization adapters for internal retrieval results and approved external provider results.
- Added scoped deduplication that never merges internal evidence across tenants or workspaces.
- Added deterministic source-aware reciprocal-rank fusion with configurable trust, freshness, and internal-priority weights.
- Added context-budget management that caps evidence count/characters while preserving citation labels.
- Added structured claim extraction, claim support verification, unsupported-claim removal, and deterministic grounded synthesis.
- Added numeric, date, status, owner/entity, and negation conflict detection with cited conflict responses.
- Added citation validation for retained evidence labels and distinct internal/external citation schemas.
- Added response fields for `outcome`, `claims`, `conflicts`, `unsupported_claims_removed`, `confidence_category`, `unified_evidence`, ranking metadata, deduplication metadata, and context-budget metadata.
- Added multi-source evidence evaluation metrics computed only from executed cases.
- Added Prometheus metrics for evidence normalization, deduplication, claim verification, unsupported claims, conflicts, citation validation/rejection, synthesis fallback, and context-budget truncation.
- Added tests for normalization, malformed evidence rejection, deduplication, ranking, context budget, claim verification, contradiction detection, citation validation, deterministic synthesis, mixed prompt injection, evaluation metrics, external regression, tenant/workspace isolation, and `/search` regression.

Completed in the previous external-tools phase:

- Added optional, disabled-by-default external-source tools: `web_search`, `wikipedia_lookup`, and `arxiv_search`.
- Added provider interfaces and adapters for disabled, deterministic test, self-hosted SearXNG, Wikipedia, and arXiv providers.
- Added strict outbound request validation for provider host allowlists, HTTPS public APIs, DNS checks, redirects, blocked private/metadata/Docker hosts, content type, timeout, and response-size limits.
- Added `allow_external_sources=false` request gating and response provenance fields for external and internal evidence.
- Added external provenance citations with provider, title, canonical URL, retrieval date, and excerpt while preserving internal chunk/document citations.
- Added external prompt-injection handling so unsafe external excerpts force abstention and clear citations.
- Added Prometheus metrics for external tool calls, failures, durations, sources used, SSRF blocks, and external timeouts without sensitive labels.
- Added optional SearXNG Docker profile and deployment documentation.
- Added deterministic tests for disabled providers, external opt-in, provider parsing, unknown providers/tools, SSRF blocks, redirects, size/content-type/timeout failures, prompt injection, provenance, internal-preference, and `/search` regression.

Completed in the previous internal-agent phase:

- Preserved existing `POST /api/v1/search` behavior and route contract.
- Kept agentic mode disabled by default behind `AGENTIC_RAG_ENABLED`.
- Extended `POST /api/v1/agent/query` into a working internal-document agent.
- Kept `GET /api/v1/agent/runs/{run_id}` workspace-scoped.
- Added typed internal tools for document metadata, query reformulation, internal search, evidence verification, retrieval diagnosis, answer synthesis, and safety review.
- Reused the validated hybrid retriever, reranker, retrieval retry, evidence sufficiency, retrieval diagnosis, citations, abstention, and LLM gateway paths.
- Added deterministic execution loop for authorization, planning, tool calls, optional retry, synthesis, citation verification, safety review, and safe fallback.
- Added structured API response fields for evidence, citations, retrieval diagnosis, tools used, safe step summaries, total duration, and fallback status.
- Added Prometheus metrics for agent runs, tool calls, replans, fallbacks, run duration, and per-tool duration without sensitive labels.
- Added tests for simple document answers, reformulation and retry, recovered retrieval, knowledge absence, partial evidence, conflicting evidence, ambiguity, max-step/tool termination, tool failure fallback, citation verification, cross-tenant denial, cross-workspace denial, prompt injection in documents, and `/search` regression.
- Added Docker Compose wiring to enable agentic mode explicitly for runtime validation while preserving the default disabled posture.
- Upgraded frontend Next.js to `16.2.11` so `npm audit --omit=dev` reports 0 vulnerabilities.

## Final Hardening

- Completed v0.2.1 operational reliability hardening for release validation:
  - Added safe re-entry handling for redelivered research report tasks so interrupted non-terminal
    jobs resume from pending retry state without duplicating completed artifacts.
  - Made research export retries clean up existing artifact rows and object keys before rewriting,
    and roll back partial object writes on export failure.
  - Added late acknowledgements and worker-lost rejection for ingestion and report Celery tasks.
  - Added optional stage-delay settings used only by outage validation probes.
  - Hardened the optional SearXNG profile with JSON response configuration and backend forwarding
    headers for local explicit opt-in validation.
  - Made OpenTelemetry Docker configuration runtime-overridable and bound the collector OTLP
    receiver on container interfaces.
  - Added `scripts/operational_validation.py` for real PostgreSQL/Redis/MinIO/Celery outage,
    restart, idempotency, cancellation, tenant-isolation, metrics, and deterministic external
    provider probes.
- Added request body size enforcement with typed `REQUEST_TOO_LARGE` responses.
- Added research concurrency and queue capacity limits with typed safe errors.
- Sanitized research artifact API serialization so object keys and signed URL signatures are not returned.
- Added `.dockerignore` files for backend and frontend to keep `.env`, databases, uploads, `node_modules`, `.next`, traces, and test output out of Docker build contexts.
- Added safe OpenTelemetry span helpers for agent query, research creation, report generation, export, artifact listing, and downloads.
- Added final evaluation metrics for knowledge absence, retrieval-failure diagnosis, source selection, and tenant isolation success.
- Added Prometheus alert rules and Grafana dashboard provisioning for the controlled agentic runtime.
- Added responsive/accessibility Playwright coverage and a stdlib local load probe script.

Completed in the previous foundation phase:

- Added disabled-by-default `POST /api/v1/agent/query`.
- Added `GET /api/v1/agent/runs/{run_id}` with workspace-scoped access.
- Preserved existing `POST /api/v1/search` behavior and route contract.
- Added configuration for agent enablement, step/tool/retry budgets, timeout, and planner provider.
- Replaced the lightweight agent scaffold with typed state, enum, schema, planner, policy, budget, registry, executor, orchestrator, and error modules.
- Added deterministic structured planner output validated by Pydantic.
- Added an allowlisted typed tool registry with enabled internal tools and disabled external placeholders.
- Added policy checks for unknown tools, disabled/network tools, forbidden arguments, direct SQL/URL/shell-like planner data, and workspace scope changes.
- Added additive persistence models and migration for `agent_runs`, `agent_steps`, and `agent_tool_calls`.
- Added audit events for agent run lifecycle.
- Added docs for controlled agent architecture and tool security.
- Added tests for transitions, planner validation, tool rejection, budgets, timeout handling, cancellation, tenant/workspace scope, disabled feature flag, safe persistence, no chain-of-thought storage, and `/search` regression.

## Completed Runtime Reliability Work

- Added deterministic-core hardening for internal-document answers: structure-aware heading/value
  chunking, section metadata for new chunks, query normalization for topic-style questions,
  attribute-aware sufficiency assessment, direct heading/value synthesis, normalized conflict
  detection, clearer search/agent result presentation, and controlled evaluation form state.
- Made completed ingestion retries idempotent: completed jobs return existing results without rewriting chunks, vectors, status, or request ids.
- Preserved existing non-null request ids through ingestion status updates.
- Disposed async database connections around Celery task event loops to avoid asyncpg cross-loop reuse.
- Added retryable dispatch states and safe Celery publishing when Redis/broker dispatch fails.
- Added a backend dispatcher loop that republishes `retry_pending` / `dispatch_failed` ingestion jobs after Redis recovery.
- Added worker Prometheus metrics for task received/completed/failed/retried counts, active tasks, queue delay, and duration.
- Added worker metrics servers and Prometheus scrape targets for ingestion, evaluation, and report workers.
- Added Playwright browser E2E coverage for registration, login, upload, ingestion, search, abstention, tenant isolation, logout, and cleanup.
- Kept Vitest and Playwright suites separate by excluding `tests/e2e/**` from Vitest.

## Docker Runtime Validation

The full observability stack was rebuilt and launched:

```text
docker compose config -> passed
docker compose build -> passed
docker compose build backend -> passed after final backend patch
docker compose --profile observability up -d -> passed
docker compose run --rm backend alembic check -> no new upgrade operations
docker compose --profile observability ps -> services healthy/running
```

Runtime probes passed:

- Completed retry for job `b1f52514-8a77-489b-afc7-40a90f6d9ae3`.
- Redis outage recovery for job `54a2de89-f572-4f83-91f3-c8cc22247702`.
- MinIO outage rollback for workspace `5396ae34-4929-4e10-bd15-254b2fba0d13`.
- Prometheus `up=1` for backend and all three worker scrape targets.

## Validation Results

- Backend tests: 116 passed, 2 skipped.
- Backend coverage: 76%.
- Controlled agent, external provider, and multi-source evidence targeted tests: 65 passed.
- Frontend unit/component tests: 24 passed.
- Frontend Playwright E2E: 1 default spec passed; 5 specs passed with gated deterministic agentic Docker mode.
- Frontend build/typecheck/lint: passed.
- Bandit, pip-audit, and npm audit: passed.
- Migration smoke: disposable SQLite Alembic `upgrade head` passed through `c8f4a2d91b77`.
- Docker smoke: `docker compose config` passed; running observability stack remained healthy.
- Agent Docker runtime: job `4982e894-bc00-4c54-b069-f79f44f7f71f` and run `20bc2a99-e839-468d-87b6-4d970909f327` passed against PostgreSQL/Redis/MinIO/Celery.
- External-disabled runtime: job `792e40b9-3357-47e7-b0db-5a4d816f5110`, internal run `4b52e7e2-2dd2-46cc-bd89-e0a5c5f16310`, public-disabled run `1db97c59-c459-4765-93ba-a8b03c4cf0ab`.
- Deterministic external runtime: public external run `e4271e7e-b199-458e-a217-f4064478cdf6`, internal-preference run `01a2870f-5ab1-4086-828c-d710c6a84f3c`.
- Research report runtime: document `d4a0ee81-3247-4cb1-92ca-8b4813589b03`, ingestion job `1985fb7d-2fd7-488b-994a-fa9bf5b0a9b6`, research job `b4653536-ffd1-4132-b513-4bd19680e5dd`, agent run `3593b650-7676-4616-b4fe-9a5d6ad33e5c`, 1 source, 1 verified citation, markdown/PDF/DOCX downloads passed.
- Agentic frontend runtime: Docker rebuilt backend/frontend with agentic flags enabled and Playwright passed 5 specs against PostgreSQL/Redis/MinIO/Celery.
- Load probes: 5/10/20-user local runs all completed with 100% success; max observed p99 was 599.1 ms.
- Optional SearXNG: container started internally and `/healthz` returned `OK`; live engine logs showed expected default-template warnings.
- Optional Ollama: local models `tinyllama:latest` and `llama3:latest` are installed; generation was not run.

## Follow-Up

- Ollama generation was not run.
- Live SearXNG search quality was not validated beyond internal container health.
- Deep destructive resilience testing was not expanded beyond prior Redis/MinIO validation and final report-worker restart.
- Coverage remains uneven in scaffolded agent/cache/security modules.
- Agentic mode remains disabled by default and should not be enabled globally until future phases add deeper operator review, dashboards, and production rollout controls.
- Arbitrary browsing, unrestricted external APIs, admin UI, and AWS deployment are intentionally not included in this phase.

## Phase 2 — Semantic Retrieval and Reranking (2026-07-28)

- Added typed, lazy, CPU-only sentence embedding and cross-encoder providers with
  allowlisted aliases, bounded inputs/batches/candidates, normalized vectors, timeout,
  retry, readiness, deterministic tests, and safe fallback.
- Upgraded indexing to `2.0`. Clean chunks embed safe title, heading, and section
  context, and record provider, alias, dimension, embedding/index versions, and time.
- Added authorized idempotent `POST /documents/{id}/reindex` and obsolete-vector
  identification.
- Calibrated the shared Search, Agent, Evaluation, and Research retriever with
  latest-version and selected-document scope, quality controls, duplicate suppression,
  safe diagnostics, and collapsible frontend labels.
- Added Recall@1/3/5, MRR, and nDCG@5 primitives without replacing historical metrics.
- No generative model, Ollama inference, AWS integration, remote inference endpoint, or
  controlled-agent replacement was introduced.

Live model validation is `PARTIAL`: neither the optional package nor a provisioned model
cache existed, and no download was attempted. Tests used the deterministic
384-dimensional provider (`deterministic-hash-v1`).

### Live completion

Operators explicitly provisioned the two fixed allowlist identifiers into a cache
outside the repository. Normal inference is now cache-only for both providers, including
development, and embedding calls have the same bounded timeout/fallback behavior as
reranking. Optional dependency ranges were advanced to patched, reproducible major
versions (`sentence-transformers>=5.2,<6`, `transformers>=5.5,<6`).

The live validation added safe benchmark, fallback, and re-index harnesses plus gated
live Chromium coverage. Obsolete-vector recommendations now compare the full configured
provider/model/dimension/version identity. A real browser run also found and fixed
horizontal overflow in the main grid and long diagnosis labels.

The implementation is operationally complete but quality status remains partial:
semantic fusion recovered one Recall@5 miss; the uncalibrated raw cross-encoder harmed
top-rank quality on the materials query, and the absent-revenue case did not abstain.
No thresholds were changed to conceal those outcomes.

## Phase 2 calibration implementation

The shared retriever now classifies deterministic query intent, emits safe reranking
policy diagnostics, and uses bounded blended reranking. Typed sufficiency decisions are
`SUFFICIENT_DIRECT`, `SUFFICIENT_COMPOSITE`, `RETRIEVAL_RETRY_REQUIRED`,
`RETRIEVAL_FAILURE_UNRESOLVED`, `KNOWLEDGE_ABSENT`, `AMBIGUOUS_QUERY`, and
`LOW_QUALITY_SOURCE`.

Numeric fact extraction preserves terminology: revenue cannot be supported by budget,
nor allowance by an unrelated amount. Answer citations select the matched supporting
span and identify the supported claim instead of returning five chunk prefixes.
Search remains the shared service consumed by controlled Agent, Evaluation, and
Research.

## Acceptance isolation

Backend authentication fixtures now register a unique organization, workspace, user,
and token per test instead of sharing a session workspace. This exposed and fixed a
real date-conflict bug: `launch` is now recognized alongside `launched`.

Chromium uploads use a run-scoped filename and exact document lookup. The acceptance
Compose override publishes non-conflicting ports under a dedicated project; project
names scope all database, cache, and object-storage volumes so cleanup can delete only
acceptance data.
# Phase 2B terminology-sensitive retrieval

Added reusable typed concept families for numerical attributes, scientific
concepts, allowance types, approval processes, roles, mathematical objects,
date types, and policy state. Candidate scoring rewards complete concept and
heading coverage, penalizes missing or contradictory sibling concepts, accounts
for extraction quality and superseded metadata, and exposes safe diagnostics.
Evidence sufficiency and citation fact selection now exclude contradictory
sources while preserving original source indexes and document authorization.

# Phase 2B agentic E2E closure

Added safe frontend/backend runtime identities and a strict Playwright
preflight. The isolated runner selects explicit default, agentic, or Phase 2B
profiles; rejects occupied alternate ports; builds current source; provisions
run-unique Compose services and volumes; verifies commit, compatibility,
readiness, and flags; runs Playwright and Alembic; and always removes disposable
state. No retrieval or product behavior required modification.

# Pre-Ollama response-state consistency

Added a shared typed response state and centralized fail-safe invariant validator
for Search, Controlled Agent, Evaluation, and Research. Deterministic claim
normalization distinguishes equivalent wording from material value, date, role,
policy, version, definition, and scope conflicts. Current metadata resolves
superseded policy evidence. API compatibility fields are derived from the
canonical state, and the frontend renders one primary status with claim-linked
citations and explicit conflict sides.

No retrieval calibration, embedding/reranker model, consumed benchmark, external
API, Ollama integration, generative model, LangChain, LangGraph, or AWS behavior
changed.
