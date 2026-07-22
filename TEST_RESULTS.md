# Test Results

Validated on 2026-07-22 from branch `feature/controlled-agentic-rag`, based on agent foundation commit `14be684`.

| Area | Test | Result | Evidence |
| --- | --- | --- | --- |
| Backend | Compilation | Pass | `.venv/bin/python -m compileall app tests` |
| Backend | Ruff lint | Pass | `.venv/bin/ruff check app tests` |
| Backend | Ruff format | Pass | `.venv/bin/ruff format --check app tests` |
| Backend | Unit/integration/security tests | Pass | `83 passed, 2 skipped` |
| Backend | Coverage | Pass | `76%` total coverage |
| Database | Alembic drift | Pass | Docker PostgreSQL `alembic check`: no new upgrade operations |
| Runtime | Docker stack | Pass | Backend, frontend, PostgreSQL, Redis, MinIO, workers, Prometheus, Grafana, and OTel running |
| Runtime | Agent internal RAG | Pass | Docker API probe job `4982e894-bc00-4c54-b069-f79f44f7f71f`, run `20bc2a99-e839-468d-87b6-4d970909f327`, 1 citation, 1 evidence item |
| Runtime | External disabled | Pass | Job `792e40b9-3357-47e7-b0db-5a4d816f5110`; public-disabled run `1db97c59-c459-4765-93ba-a8b03c4cf0ab`; no external access performed |
| Runtime | External deterministic | Pass | Public run `e4271e7e-b199-458e-a217-f4064478cdf6`; deterministic provider, external citation, provenance returned |
| Runtime | Internal preferred | Pass | Run `01a2870f-5ab1-4086-828c-d710c6a84f3c`; no external tool called when internal evidence was sufficient |
| Runtime | Completed-task retry | Pass | Same request id, 1 chunk, 1 embedded chunk, no asyncpg/event-loop log matches |
| Runtime | Redis outage recovery | Pass | Upload became `retry_pending`; automatic dispatcher completed it after Redis restart |
| Runtime | Orphan retry jobs | Pass | `0` jobs in `retry_pending` or `dispatch_failed` after recovery |
| Runtime | MinIO outage | Pass | Sanitized 500 and no document row persisted |
| Observability | Prometheus targets | Pass | `backend:8000`, `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103` all `up=1` |
| Observability | Worker metrics | Pass | `ekip_worker_tasks_completed_total{worker_role="ingestion"} = 4` |
| Frontend | Lint | Pass | 0 errors, 1 existing Fast Refresh warning |
| Frontend | Typecheck | Pass | `npm run typecheck` |
| Frontend | Unit/component tests | Pass | 5 files, 19 tests passed |
| Frontend | Browser E2E | Pass | 1 Playwright Chromium spec passed against Dockerized frontend/backend |
| Frontend | Build | Pass | `npm run build` |
| Security | Bandit | Pass | No issues |
| Security | pip-audit | Pass | No known vulnerabilities for audited PyPI packages |
| Security | npm audit | Pass | 0 vulnerabilities |
| Agent | State transitions | Pass | Valid and invalid transition tests |
| Agent | Deterministic planner | Pass | Structured internal-document tool plan |
| Agent | Tool policy | Pass | Unknown tool, forbidden scope change, disabled/network placeholders rejected |
| Agent | Budgets and timeout | Pass | Step budget and per-tool timeout tests |
| Agent | Feature flag | Pass | `AGENTIC_RAG_ENABLED=false` returns clear disabled response |
| Agent | Persistence safety | Pass | Runs, steps, tool calls, and audit events store operational summaries only |
| Agent | Internal document question | Pass | Simple document answer with verified citation |
| Agent | Reformulation and retry | Pass | Query reformulation triggers second internal retrieval |
| Agent | Retrieval outcomes | Pass | Knowledge absence, partial evidence, conflicting evidence, and ambiguity cases |
| Agent | Tool failure fallback | Pass | Safe fallback to adaptive RAG preserves authorization and marks `fallback_used=true` |
| Agent | Tenant/workspace isolation | Pass | Cross-tenant and cross-workspace agent queries return no leaked evidence |
| Agent | Prompt injection | Pass | Uploaded document instruction injection forces safe abstention |
| Agent | External providers | Pass | Disabled, deterministic, SearXNG parsing, Wikipedia parsing, and arXiv parsing tests |
| Agent | SSRF protections | Pass | Private IPv4/IPv6, localhost, metadata host, Docker hostname, blocked scheme, and private redirect tests |
| Agent | External provenance | Pass | External citation fields remain separate from internal document citation fields |
| Agent | Cancellation | Pass | Cancelled orchestrator run persisted as `cancelled` |
| Regression | Existing search endpoint | Pass | `/api/v1/search` still returns answer and retrieval diagnosis |
| Migration | Agent tables | Pass | Disposable SQLite Alembic `upgrade head` reached `c8f4a2d91b77` |
| Docker | Smoke | Pass | `docker compose config`; rebuilt backend and frontend images; observability stack healthy |
| Docker | Web-search profile | Pass | `docker compose --profile web-search config` |
| Observability | Agent metrics | Pass | All requested agent metric families exposed without sensitive labels |

## Notes

- `npm run test` initially collected `tests/e2e/runtime.spec.ts`; `vitest.config.ts` now excludes `tests/e2e/**`.
- `npm audit --omit=dev` identified vulnerable transitive `sharp <0.35.0`; a targeted `sharp@0.35.3` override was applied instead of the audit-suggested breaking Next downgrade, and the audit now reports 0 vulnerabilities.
- Host-side API and browser validation required sandbox escalation to reach Docker-published localhost ports.
