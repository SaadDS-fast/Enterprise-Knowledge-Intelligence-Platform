# Agent Tool Security

Updated on 2026-07-22.

## Default Posture

Agentic RAG is disabled by default:

```env
AGENTIC_RAG_ENABLED=false
```

The platform must not silently route `/search` traffic into the agent. `/agent/query` is the only agent entrypoint.

## Tool Boundary

The tool registry is allowlist based. A planner can only select tools registered in `ToolRegistry`.

This phase permits only internal, tenant-scoped tools:

- `document_metadata`
- `query_reformulation`
- `internal_search`
- `evidence_verifier`
- `retrieval_diagnosis`
- `answer_synthesizer`
- `safety_reviewer`

Network-required tools are rejected. Disabled placeholders cannot claim success.

## Rejected Capabilities

The policy layer rejects planner output containing:

- shell commands
- direct SQL
- arbitrary URLs
- external endpoints
- unauthorized workspace changes
- unknown tools
- too many steps or tool calls

These checks apply before tool execution.

## Tenant And Workspace Scope

The API uses the existing authenticated tenant dependency. The orchestrator receives a `TenantContext` and passes only the authorized `workspace_id` into tools. Tool arguments cannot override the workspace.

Retrieval and fallback paths preserve the same workspace and optional document filters. Cross-tenant and cross-workspace queries against uploaded document content return no evidence instead of leaking document text.

Stored runs are scoped by:

- `tenant_id`
- `workspace_id`
- `user_id`

`GET /agent/runs/{run_id}` returns 404 for runs outside the caller's workspace.

## Persistence Safety

Agent persistence stores concise operational records, not private reasoning.

Allowed examples:

- `Tenant workspace scope authorized`
- `Internal document search completed`
- `Final citations verified`

Disallowed examples:

- hidden reasoning traces
- chain-of-thought
- raw planner scratchpads
- credentials or tokens

## Audit Events

Agent run creation, completion, and cancellation create audit events with sanitized summaries. Audit details do not contain prompts beyond the stored user query already present on `agent_runs`.

## Prompt Injection

The safety reviewer scans the user query, retrieved evidence, and drafted answer for prompt-injection signals. Uploaded documents that ask the model to ignore prior or system instructions force safe abstention.

## Future Tool Review

Before enabling any external tool, require:

- explicit tool registration
- network-required review
- per-tool timeout
- maximum result size
- tenant scope verification
- audit events
- tests for safe failure and disabled behavior
