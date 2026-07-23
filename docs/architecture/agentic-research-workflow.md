# Agentic Research Workflow

The research workflow is disabled by default and runs only when `AGENT_RESEARCH_ENABLED=true`.
It reuses the controlled agent rather than creating a separate retrieval path.

Flow:

1. Authorize tenant, workspace, user, and optional document scope.
2. Enforce idempotency, concurrency, queue-depth, budget, timeout, source, and format controls.
3. Persist a scoped `research_jobs` row.
4. Dispatch to the `report-worker` queue or local background task according to `JOB_EXECUTION_MODE`.
5. Run the controlled agent with research budgets.
6. Verify evidence, claims, conflicts, and citations.
7. Render markdown, PDF, and DOCX through the storage abstraction.
8. Store artifacts under tenant/workspace/job-scoped object keys.
9. Expose authenticated short-lived download URLs without returning object keys or raw signatures.

The worker rechecks workspace scope before generation. Cancellation transitions to
`CANCEL_REQUESTED` and is honored at bounded stage boundaries.
