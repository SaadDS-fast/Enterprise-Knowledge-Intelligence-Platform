# Case Study: Controlled Agentic RAG for Enterprise Documents

## Real-World Problem

Internal teams need answers from private documents, but enterprise document assistants fail when they behave like generic chatbots. A useful system must answer from scoped evidence, cite sources, and say "I do not know" when the workspace lacks enough information.

The harder requirement is operational trust. The system must survive background-worker retries, prevent cross-tenant evidence leaks, avoid fabricated citations, handle prompt injection inside uploaded documents, and distinguish retrieval failure from actual knowledge absence.

## Project Goal

Enterprise Knowledge Intelligence Platform, or EKIP, implements a local-first multi-tenant document intelligence platform with:

- stable standard RAG through `POST /api/v1/search`;
- disabled-by-default controlled agentic RAG through `POST /api/v1/agent/query`;
- asynchronous cited research reports through `/api/v1/agent/research`;
- real Docker validation with PostgreSQL, Redis, MinIO, Celery workers, Prometheus, Grafana, and OpenTelemetry.

## Design Decisions

### Preserve Standard Search

The existing `/api/v1/search` endpoint remains the stable non-agentic path. This keeps a simple, predictable RAG surface for users and tests while allowing agentic behavior to evolve separately.

### Use Typed Internal Tools

The agent runtime uses typed tools for internal search, document metadata, query reformulation, evidence verification, retrieval diagnosis, answer synthesis, and safety review. Tool outputs are structured and auditable.

### Keep Agentic Mode Disabled By Default

Agentic RAG, research reports, and external-source tools are off unless explicitly enabled by backend and frontend feature flags. This makes the default local experience lower risk and zero-cost.

### Make Retrieval Outcomes Explicit

The system distinguishes:

- sufficient evidence;
- evidence recovered after retry;
- unresolved retrieval failure;
- knowledge absence;
- partial evidence;
- conflicting evidence;
- ambiguous query.

That distinction is critical for trust. A user should know whether the system could not retrieve evidence or whether the workspace does not appear to contain the answer.

## Why A Custom Controlled Agent Runtime Was Used

The project intentionally uses a custom orchestration layer instead of adopting a broad autonomous-agent framework as the core runtime. The goal was not maximum agent freedom; it was controlled, inspectable internal-document reasoning.

The custom runtime makes these constraints direct:

- deterministic planning;
- allowlisted tools;
- tenant/workspace scope checks;
- bounded steps and timeouts;
- safe fallback behavior;
- safe run summaries without hidden reasoning;
- low-cardinality metrics;
- citation and evidence verification before final response.

Frameworks such as LangGraph or LangChain can be useful, but this implementation favors a small explicit runtime so every security and reliability rule is visible in the codebase.

## Why Unrestricted Agents Were Rejected

Unrestricted agents were rejected because they expand the attack surface beyond the product goal. EKIP does not provide tools for arbitrary shell commands, direct SQL, unscoped filesystem access, unrestricted HTTP browsing, or user-supplied URL fetching.

Retrieved documents are treated as untrusted input. An uploaded document can contain malicious instructions, but those instructions should never control tool selection, authorization scope, or external access.

## Multi-Tenant Security

Security boundaries are enforced across:

- organizations and workspaces;
- documents and document versions;
- chunks and citations;
- agent runs and tool calls;
- research jobs and artifacts;
- signed artifact downloads.

The validation matrix includes cross-tenant and cross-workspace denial cases. The final operational validation recorded denial behavior for cross-document reference, research read, artifact metadata, artifact download, and agent-run read attempts.

## Resilience Testing

The v0.2.1 operational-hardening validation exercised the real Docker stack:

- Redis dispatch outage recovered safely.
- MinIO export outage recovered without duplicate artifacts.
- Backend restart completed an in-flight research job.
- Report worker restart recovered.
- Ingestion worker restart recovered.
- PostgreSQL interruption returned a sanitized error and then recovered.
- Cancellation and idempotency paths stayed safe.

The validation script is [scripts/operational_validation.py](../../scripts/operational_validation.py).

## Evaluation Results

Latest recorded validation:

- Backend tests: `117 passed, 2 skipped`.
- Backend coverage: `76%`.
- Frontend tests: 9 Vitest files and 24 tests passed.
- Default Playwright: `1 passed, 4 skipped`.
- Enabled agentic Playwright: `5 passed`.
- Bandit: no issues.
- pip-audit: no known vulnerabilities for audited packages.
- npm audit: 0 vulnerabilities.
- Docker Compose config: default, observability, and web-search profiles passed.
- Alembic: upgrade and drift check passed.
- Live SearXNG opt-in path returned external evidence and citations through `/agent/query`.
- Prometheus, Grafana, and OpenTelemetry were API/log validated.

## Limitations

- This is a local-first portfolio project, not a claimed production deployment.
- Agentic RAG, research reports, and external tools are disabled by default.
- Local load probes are not enterprise capacity benchmarks.
- Live public search quality depends on the local SearXNG environment and internet availability.
- Some scaffolded enterprise modules remain lower coverage.
- Screenshots still need to be captured and added.

## What This Demonstrates

This repository demonstrates backend architecture, frontend integration, multi-tenant data design, RAG evaluation, controlled agent orchestration, secure-by-default feature gating, Docker runtime validation, and operational documentation.
