# Controlled Agentic RAG Architecture

Updated on 2026-07-22.

## Scope

The controlled agent remains disabled by default and fully supports an internal-document-only mode. It also has optional approved external-source tools for web search, Wikipedia, and arXiv. This phase adds a disabled-by-default asynchronous cited research-report workflow. It does not add arbitrary browsing, major frontend changes, autonomous multi-agent behavior, AWS deployment, or unrestricted external APIs.

Existing search remains unchanged:

- `POST /api/v1/search`

Agentic behavior is separate:

- `POST /api/v1/agent/query`
- `GET /api/v1/agent/runs/{run_id}`
- `POST /api/v1/agent/research`
- `GET /api/v1/agent/research`
- `GET /api/v1/agent/research/{job_id}`
- `POST /api/v1/agent/research/{job_id}/cancel`
- `GET /api/v1/agent/research/{job_id}/artifacts`
- `GET /api/v1/agent/research/{job_id}/download/{format}`

When `AGENTIC_RAG_ENABLED=false`, `/agent/query` returns a clear feature-disabled response and does not run the orchestrator.

When `AGENT_RESEARCH_ENABLED=false`, `/agent/research` returns a clear feature-disabled response and does not dispatch a report job.

## State Machine

The orchestrator uses explicit states:

- `receive_request`
- `authorize`
- `classify_intent`
- `create_plan`
- `select_tool`
- `execute_tool`
- `assemble_evidence`
- `verify_evidence`
- `replan`
- `synthesize`
- `safety_review`
- `complete`
- `failed`
- `cancelled`

Transitions are allowlisted in `backend/app/agents/state.py`. Invalid transitions raise before persistence can represent an impossible flow.

## Execution Loop

The agent follows a deterministic internal-document loop:

- query intake
- authorization through the existing tenant dependency
- intent classification as an internal document question
- deterministic planning
- typed tool selection
- internal retrieval through the existing hybrid retriever and reranker
- evidence verification
- optional query reformulation and second retrieval
- retrieval diagnosis
- answer synthesis with citations
- citation and safety review
- final response

The run stops on sufficient evidence, absent evidence, ambiguity, conflicting evidence, maximum tool or retry budget, timeout, cancellation, or safe fallback.

External access is a guarded branch after internal retrieval and diagnosis. It runs only when `allow_external_sources=true` on the request and the relevant feature flag is enabled. Internal evidence remains preferred; organization-specific questions that have sufficient internal evidence do not call external tools.

## Planner

The default planner is deterministic and local. It emits structured Pydantic-validated plans, not executable free-form instructions.

Default plan:

```json
{
  "intent": "document_question",
  "steps": [
    {
      "tool": "document_metadata",
      "purpose": "Document metadata scoped to workspace selected",
      "required": true
    },
    {
      "tool": "query_reformulation",
      "purpose": "Query normalization selected",
      "required": true
    },
    {
      "tool": "internal_search",
      "purpose": "Internal document search selected",
      "required": true
    },
    {
      "tool": "evidence_verifier",
      "purpose": "Evidence verification selected",
      "required": true
    },
    {
      "tool": "retrieval_diagnosis",
      "purpose": "Retrieval diagnosis selected",
      "required": true
    },
    {
      "tool": "answer_synthesizer",
      "purpose": "Answer synthesis selected",
      "required": true
    },
    {
      "tool": "safety_reviewer",
      "purpose": "Safety review selected",
      "required": true
    }
  ]
}
```

Future planner providers can be added behind the `AGENT_PLANNER_PROVIDER` setting, but must still return the same structured schema.

## Tool Registry

Tools are typed definitions with:

- name
- description
- input schema
- output schema
- required permission
- timeout
- maximum result size
- maximum result count
- maximum response size
- network-required flag
- feature flag
- enabled flag
- execution handler

Registered tools:

- `document_metadata`: enabled; returns safe workspace document counts.
- `query_reformulation`: enabled; normalizes queries and expands retry terms.
- `internal_search`: enabled; calls existing internal RAG search within the authorized workspace.
- `evidence_verifier`: enabled; records structured evidence sufficiency and term coverage.
- `retrieval_diagnosis`: enabled; distinguishes recovered retrieval, unresolved retrieval, knowledge absence, partial evidence, conflicting evidence, and ambiguity.
- `answer_synthesizer`: enabled; uses existing LLM gateway, citation appending, and abstention helpers.
- `safety_reviewer`: enabled; blocks prompt-injection signals from the query, evidence, or drafted answer.
- `web_search`: enabled registry entry; returns disabled output unless `allow_external_sources=true`, `AGENT_WEB_SEARCH_ENABLED=true`, and a configured approved provider is available.
- `wikipedia_lookup`: enabled registry entry; returns disabled output unless `allow_external_sources=true` and `AGENT_EXTERNAL_APIS_ENABLED=true`.
- `arxiv_search`: enabled registry entry; returns disabled output unless `allow_external_sources=true` and `AGENT_EXTERNAL_APIS_ENABLED=true`.
- `external_web_search`: disabled placeholder; it cannot execute successfully in this phase.

Every enabled tool returns structured output with `tool`, `status`, safe summary fields, and tool-specific metadata. Tool outputs never include hidden reasoning.

## Research Report Workflow

The report workflow reuses the controlled agent and validated services instead of creating a separate retrieval path. A request is persisted as a `research_jobs` row, dispatched to the existing `report-worker` queue when `JOB_EXECUTION_MODE=celery`, and run through a bounded state machine:

- `PENDING`
- `AUTHORIZING`
- `PLANNING`
- `RETRIEVING`
- `RETRIEVAL_RETRY`
- `AGGREGATING_EVIDENCE`
- `VERIFYING_EVIDENCE`
- `WRITING`
- `VERIFYING_CITATIONS`
- `SAFETY_REVIEW`
- `EXPORTING`
- `COMPLETED`
- `FAILED`
- `CANCEL_REQUESTED`
- `CANCELLED`

The workflow enforces tenant and workspace scope before dispatch and again in the worker. Optional `document_ids` are validated against the authorized workspace. Idempotency is scoped by tenant, workspace, user, request idempotency key, question, document scope, formats, and source policy.

Structured reports include executive summary, methodology, key findings, detailed analysis, internal evidence, optional external evidence, conflicting evidence, information gaps, limitations, conclusions, citations, and generation metadata. Artifacts are written through the object-storage abstraction under tenant/workspace/job-scoped `reports/...` keys and exposed through short-lived signed download parameters.

Export formats are controlled by `AGENT_RESEARCH_ALLOWED_FORMATS` and currently support `markdown`, `pdf`, and `docx`.

## Persistence

The additive migration `c8f4a2d91b77_agent_orchestration_tables.py` creates:

- `agent_runs`
- `agent_steps`
- `agent_tool_calls`

The tables store operational summaries only. Private chain-of-thought is not stored.

Examples of persisted summaries:

- `Internal document search selected`
- `Evidence insufficient; retrieval retry requested`
- `Final citations verified`

## Budgets And Safety

Configured budgets:

- `AGENT_MAX_STEPS=6`
- `AGENT_MAX_TOOL_CALLS=12`
- `AGENT_TIMEOUT_SECONDS=90`
- `AGENT_MAX_RETRIEVAL_RETRIES=2`
- `AGENT_WEB_SEARCH_ENABLED=false`
- `WEB_SEARCH_PROVIDER=disabled`
- `WEB_SEARCH_MAX_RESULTS=5`
- `WEB_SEARCH_TIMEOUT_SECONDS=10`
- `WEB_SEARCH_MAX_RESPONSE_BYTES=1000000`
- `AGENT_EXTERNAL_APIS_ENABLED=false`
- `SEARXNG_URL=http://searxng:8080`
- `EVIDENCE_MAX_ITEMS=12`
- `EVIDENCE_MAX_INTERNAL_ITEMS=8`
- `EVIDENCE_MAX_EXTERNAL_ITEMS=6`
- `AGENT_RESEARCH_ENABLED=false`
- `AGENT_RESEARCH_MAX_STEPS=12`
- `AGENT_RESEARCH_MAX_TOOL_CALLS=20`
- `AGENT_RESEARCH_MAX_SOURCES=20`
- `AGENT_RESEARCH_TIMEOUT_SECONDS=300`
- `AGENT_RESEARCH_MAX_REPORT_WORDS=5000`
- `AGENT_RESEARCH_EXTERNAL_SOURCES_DEFAULT=false`
- `AGENT_RESEARCH_ALLOWED_FORMATS=markdown,pdf,docx`
- `AGENT_RESEARCH_SIGNED_URL_TTL_SECONDS=600`
- `EVIDENCE_CONTEXT_MAX_CHARS=12000`
- `EVIDENCE_RRF_K=60`
- `EVIDENCE_INTERNAL_PRIORITY_WEIGHT=1.0`
- `EVIDENCE_EXTERNAL_TRUST_WEIGHT=0.8`
- `EVIDENCE_MIN_SUPPORT_SCORE=0.65`

The policy layer rejects:

- unknown tools
- disabled tools
- network-required tools when the request did not allow external sources or the feature flag is disabled
- forbidden arguments such as shell commands, URLs, endpoints, or SQL
- unauthorized workspace scope changes
- plans that exceed budget

Failures are persisted as safe summaries and surfaced through controlled API errors.

## API Response

`POST /api/v1/agent/query` returns:

- `run_id`
- `status`
- `answer`
- `abstained`
- `citations`
- `evidence`
- `internal_evidence`
- `external_evidence`
- `external_sources_used`
- `providers_used`
- `external_access_allowed`
- `external_access_performed`
- `retrieval_diagnosis`
- `tools_used`
- `safe_step_summaries`
- `total_duration_ms`
- `fallback_used`
- `outcome`
- `claims`
- `conflicts`
- `unsupported_claims_removed`
- `confidence_category`
- `unified_evidence`
- `evidence_ranking`
- `evidence_deduplication`
- `context_budget`

The response does not expose hidden reasoning. If the agent fails before producing a safe result, it may invoke the existing adaptive `/search` service internally, sets `fallback_used=true`, logs the reason on the run, and preserves the same authorization scope.

Unified evidence normalization, source-aware rank fusion, context-budget trimming, claim verification, conflict detection, citation validation, and deterministic synthesis are described in `docs/architecture/multi-source-evidence.md`.

## Deterministic Internal-Document Core

The internal-document core does not require Ollama or any external model. It uses deterministic
query normalization, hybrid retrieval, reranking, attribute-aware support assessment,
heading/value extraction, citation validation, and abstention. Direct facts such as
`Topic: Functions` can answer topic questions even when generic similarity is moderate, provided
the cited evidence belongs to the authorized tenant/workspace.

Conflict handling compares values for the same normalized requested attribute. Unrelated facts
such as tutor qualification or teaching method are not contradictions for a demo-topic question.
Confirmed conflicts return the conflicting values and citations and ask the user to clarify which
source or version should govern the answer.

Newly ingested documents receive structure-aware chunks and section metadata. Existing document
versions should be re-uploaded or reprocessed to benefit from the improved chunk boundaries.

## Metrics

Prometheus exports agent counters and histograms without query, document, user, tenant, or filename labels:

- `ekip_agent_runs_started_total`
- `ekip_agent_runs_completed_total`
- `ekip_agent_runs_failed_total`
- `ekip_agent_tool_calls_total{tool=...}`
- `ekip_agent_replans_total`
- `ekip_agent_fallbacks_total`
- `ekip_agent_duration_seconds`
- `ekip_agent_tool_duration_seconds{tool=...}`
- `ekip_agent_external_tool_calls_total{provider=...,tool=...,outcome=...}`
- `ekip_agent_external_tool_failures_total{provider=...,tool=...,outcome=...}`
- `ekip_agent_external_tool_duration_seconds{provider=...,tool=...,outcome=...}`
- `ekip_agent_external_sources_used_total{provider=...,tool=...}`
- `ekip_agent_ssrf_blocks_total{provider=...,outcome=...}`
- `ekip_agent_external_timeouts_total{provider=...,tool=...}`
- `ekip_agent_evidence_items_total{source_type=...}`
- `ekip_agent_evidence_deduplicated_total{source_type=...}`
- `ekip_agent_claims_verified_total{verification_status=...}`
- `ekip_agent_claims_unsupported_total{outcome=...}`
- `ekip_agent_conflicts_detected_total{outcome=...}`
- `ekip_agent_citations_validated_total{source_type=...,outcome=...}`
- `ekip_agent_citations_rejected_total{outcome=...}`
- `ekip_agent_synthesis_fallbacks_total{outcome=...}`
- `ekip_agent_context_budget_truncations_total{outcome=...}`
