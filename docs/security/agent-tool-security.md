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

The default mode permits only internal, tenant-scoped tools:

- `document_metadata`
- `query_reformulation`
- `internal_search`
- `evidence_verifier`
- `retrieval_diagnosis`
- `answer_synthesizer`
- `safety_reviewer`

Optional external tools are registered but gated:

- `web_search`
- `wikipedia_lookup`
- `arxiv_search`

Network-required tools are rejected unless the request has `allow_external_sources=true` and the relevant feature flag is enabled. When disabled, external tools return typed disabled results and make no network call. Disabled placeholders cannot claim success.

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

## Evidence And Prompt Injection

Retrieved internal and external text remains evidence only. It cannot modify the plan, enable tools, weaken authorization, change ranking policy, or become executable instructions.

The safety reviewer scans the user query, cited evidence in the unified evidence path, and drafted answer for prompt-injection signals. Uploaded documents that ask the model to ignore prior or system instructions force safe abstention when that document is cited or used.

External excerpts are scanned the same way. They are treated as untrusted source text and cannot authorize tools, change tenant/workspace scope, request credentials, trigger shell commands, or override evidence rules.

Claim verification and citation validation happen before the safety review, so unrelated retrieved text does not poison a response that is grounded in different cited evidence.

## Future Tool Review

Before enabling any external tool, require:

- explicit tool registration
- network-required review
- per-tool timeout
- maximum result size
- tenant scope verification
- audit events
- tests for safe failure and disabled behavior
