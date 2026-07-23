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
