# Interview Guide

## 20 Likely Technical Questions

### 1. What problem does EKIP solve?

It helps teams query private document workspaces with cited answers, controlled agent workflows, research-report generation, and tenant isolation. The focus is trustworthy internal-document intelligence, not generic chatbot behavior.

### 2. Why is standard RAG not enough?

Standard RAG often retrieves chunks and returns generated text without enough diagnosis, citation validation, retry discipline, tenant isolation, or prompt-injection handling. EKIP adds structured retrieval diagnosis, evidence verification, conflict handling, and safe abstention.

### 3. What is controlled agentic RAG in this project?

It is a bounded orchestration loop over typed tools: authorize, plan deterministically, retrieve internal evidence, verify evidence, optionally reformulate and retry, synthesize, validate citations, run safety review, and return a structured response.

### 4. Why did you build custom orchestration instead of using LangGraph or LangChain?

The project optimizes for explicit security and auditability. A small custom runtime makes tool allowlists, scope checks, budgets, timeout behavior, fallback, and persistence easy to inspect. LangGraph or LangChain could be integrated later, but the core constraints are simple enough to own directly.

### 5. What trade-off comes with custom orchestration?

It avoids framework complexity and makes security rules explicit, but it means less ecosystem functionality out of the box. More complex branching workflows would require more local implementation.

### 6. How is tenant isolation enforced?

Tenant and workspace IDs are carried through API dependencies, database queries, document scopes, agent runs, research jobs, artifact metadata, and downloads. Cross-tenant and cross-workspace tests validate denial behavior.

### 7. What prevents an uploaded document from controlling the agent?

Retrieved text is treated as evidence, not instructions. The agent uses deterministic planning and allowlisted typed tools. Prompt-injection scanning can force abstention, and document text cannot change tenant scope or enable tools.

### 8. What tools can the agent use?

The internal tool set includes internal search, document metadata, query reformulation, evidence verifier, retrieval diagnosis, answer synthesizer, and safety reviewer. External tools are disabled by default and require explicit flags plus request opt-in.

### 9. How do you distinguish retrieval failure from knowledge absence?

The retrieval diagnosis service records evidence counts, support scores, retry status, reason codes, and final diagnosis. Retrieval failure suggests retry or system inspection; knowledge absence means the workspace does not contain enough evidence.

### 10. What happens when evidence is partial?

The agent can return a partial-evidence outcome, abstain, or produce a constrained answer depending on support score and verification. Unsupported claims are removed before synthesis.

### 11. How are citations verified?

Citation labels must correspond to retained evidence. The system validates citation references and rejects unrelated or unknown labels. External citations remain separate from internal document citations.

### 12. How are conflicts handled?

The evidence layer detects practical contradictions such as numeric, date, owner/entity, status, and negation conflicts. Conflicting evidence can produce a conflict outcome instead of an overconfident answer.

### 13. How does the research-report workflow work?

`POST /api/v1/agent/research` creates a scoped job, dispatches it to the report worker, runs the controlled agent, builds a structured report, renders markdown/PDF/DOCX, stores artifacts, and exposes short-lived download URLs.

### 14. How is idempotency handled for reports?

Research idempotency includes tenant, workspace, user, request key, question, document scope, formats, and source policy. Replays return the same job instead of duplicating work.

### 15. What resilience testing was done?

Operational validation covered Redis dispatch outage recovery, MinIO export outage recovery, backend restart, report-worker restart, ingestion-worker restart, PostgreSQL interruption recovery, cancellation, idempotency, and tenant-isolation denial.

### 16. What does Docker run locally?

Default Docker runs backend, frontend, PostgreSQL, Redis, MinIO, ingestion worker, evaluation worker, and report worker. Profiles add Prometheus/Grafana/OpenTelemetry or SearXNG.

### 17. What observability exists?

The backend and workers expose Prometheus metrics. Grafana has an `EKIP Agentic Runtime` dashboard. OpenTelemetry collector support was validated by logging a backend trace batch.

### 18. What are the most important security controls?

Tenant/workspace scope, typed tool allowlists, disabled-by-default agent/external flags, upload validation, request-size limits, SSRF controls, signed artifact URLs, prompt-injection handling, and safe run summaries.

### 19. What are the key validation numbers?

Latest recorded validation: backend `117 passed, 2 skipped`, 76% coverage; frontend 24 Vitest tests; enabled Playwright 5 tests; Bandit clean; pip-audit no known vulnerabilities for audited packages; npm audit 0 vulnerabilities.

### 20. What would you build next?

Captured screenshots, a hosted demo only after deployment exists, expanded evaluation datasets, enterprise identity provider integration, deeper alert/trace validation, backup/restore drills, and improved coverage for scaffolded modules.

## Architecture Trade-Offs

- **Local-first default:** easier to evaluate without paid APIs, but not a production deployment claim.
- **Deterministic local behavior:** good for repeatable validation, less impressive than a large hosted model unless optional providers are enabled.
- **Typed tools:** safer and testable, less flexible than arbitrary agent tools.
- **Separate `/search` and `/agent/query`:** preserves stable behavior, adds more API surface.
- **Celery report workflow:** realistic resilience and idempotency behavior, more moving parts than inline export.

## Interview Talking Points

- Focus on why trust boundaries matter more than raw generation quality.
- Mention that unrestricted agents were rejected intentionally.
- Use the retrieval-failure versus knowledge-absence distinction as the core RAG insight.
- Use the v0.2.1 validation results as evidence, not vague claims.
- Be explicit that AWS deployment, CI, and screenshots are not claimed unless added later.
