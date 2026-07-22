# Agentic Frontend Workspace

The agentic knowledge workspace is isolated under `/agent` and is disabled by default. The
existing `/search` route remains the stable adaptive RAG interface and `/research` remains the
legacy synchronous brief workflow.

## Routes

- `/agent` submits controlled internal-document questions to `POST /api/v1/agent/query`.
- `/agent/runs/[runId]` displays safe execution summaries, tool names, statuses, durations,
  and sanitized errors from `GET /api/v1/agent/runs/{run_id}`.
- `/agent/research` submits asynchronous cited report jobs to `POST /api/v1/agent/research`.
- `/agent/research/[jobId]` polls job state, supports cancellation, and downloads completed
  artifacts through authenticated, short-lived URLs.

## Feature Flags

The frontend uses build-time `NEXT_PUBLIC_*` flags so hidden routes and navigation remain
unavailable unless explicitly enabled:

- `NEXT_PUBLIC_AGENTIC_RAG_ENABLED`
- `NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED`
- `NEXT_PUBLIC_AGENT_EXTERNAL_SOURCES_ENABLED`
- `NEXT_PUBLIC_AGENT_POLL_INTERVAL_MS`

Backend authorization and backend feature flags remain authoritative. Frontend flags only decide
whether the user interface is shown.

## Data Handling

The workspace renders only structured safe fields returned by the API: answer, outcome,
citations, evidence snippets, retrieval diagnosis, claim status, conflicts, tool names, and
safe step summaries. It does not render hidden reasoning. Recent run IDs are stored locally for
navigation convenience; answers, document text, signed URLs, users, tenants, and filenames are
not stored in browser-local telemetry by this implementation.

External-source UI is hidden unless `NEXT_PUBLIC_AGENT_EXTERNAL_SOURCES_ENABLED=true`. External
URLs are rendered only when they parse as `http` or `https` and always use
`rel="noopener noreferrer"`.
