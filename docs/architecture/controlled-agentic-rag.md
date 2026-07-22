# Controlled Agentic RAG Architecture

Updated on 2026-07-22.

## Scope

This phase turns the disabled-by-default controlled agent foundation into a working internal-document RAG agent. It does not add web search, external APIs, autonomous research reports, report exports, or major frontend changes.

Existing search remains unchanged:

- `POST /api/v1/search`

Agentic behavior is separate:

- `POST /api/v1/agent/query`
- `GET /api/v1/agent/runs/{run_id}`

When `AGENTIC_RAG_ENABLED=false`, `/agent/query` returns a clear feature-disabled response and does not run the orchestrator.

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
- network-required flag
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
- `external_web_search`: disabled placeholder; it cannot execute successfully in this phase.

Every enabled tool returns structured output with `tool`, `status`, safe summary fields, and tool-specific metadata. Tool outputs never include hidden reasoning.

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

The policy layer rejects:

- unknown tools
- disabled tools
- network-required tools in this phase
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
- `retrieval_diagnosis`
- `tools_used`
- `safe_step_summaries`
- `total_duration_ms`
- `fallback_used`

The response does not expose hidden reasoning. If the agent fails before producing a safe result, it may invoke the existing adaptive `/search` service internally, sets `fallback_used=true`, logs the reason on the run, and preserves the same authorization scope.

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
