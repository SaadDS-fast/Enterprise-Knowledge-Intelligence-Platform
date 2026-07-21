# Controlled Agentic RAG Architecture

Updated on 2026-07-21.

## Scope

This phase adds a disabled-by-default controlled agent orchestration foundation. It does not add web search, external APIs, autonomous research reports, or major frontend changes.

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

## Planner

The default planner is deterministic and local. It emits structured Pydantic-validated plans, not executable free-form instructions.

Default plan:

```json
{
  "intent": "document_question",
  "steps": [
    {
      "tool": "internal_search",
      "purpose": "Internal document search selected",
      "required": true
    },
    {
      "tool": "evidence_verifier",
      "purpose": "Evidence verification selected",
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

- `internal_search`: enabled; calls existing internal RAG search within the authorized workspace.
- `evidence_verifier`: enabled; records concise evidence sufficiency status.
- `external_web_search`: disabled placeholder; it cannot execute successfully in this phase.

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
- `AGENT_MAX_TOOL_CALLS=8`
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
