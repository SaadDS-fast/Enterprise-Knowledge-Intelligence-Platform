# Test Results

## Verifiable Answer Passport Phase 3B independent audit — 2026-08-02

- Focused Phase 3B: 16 persistence/export/API tests passed (12 before audit plus 4 audit tests);
  combined passport regression selection contains 177 tests.
- Full backend: 402 passed, 4 environment-gated skips; 81% total coverage. Phase 3B coverage:
  persistence 84%, repository 78%, model 100%, API 64%.
- Compileall and Ruff passed. Changed modules pass Mypy; repository application Mypy retains 42
  pre-existing errors in unrelated modules. Bandit found zero issues; pip-audit found no known
  vulnerabilities and skipped only the unpublished local package.
- Frontend clean install, lint (0 errors/1 known warning), typecheck, 11 files/27 tests, production
  build, and npm production audit (0 vulnerabilities) passed. No frontend file changed.
- Docker Compose config and backend build passed. Isolated PostgreSQL parent→Phase 3B upgrade,
  drift check, cross-organization INSERT denial, direct UPDATE/DELETE denial, downgrade, re-upgrade,
  unrelated-row preservation, and single-head check passed.
- Isolated default Playwright passed 1 runtime test with 8 feature-gated skips. No consumed grounding
  holdout ran.

## Verifiable Answer Passport Phase 3A independent audit — 2026-08-02

- Lifecycle/trust/issuance focused set: 62 passed (40 prior plus 22 independent audit cases).
  Broader passport core and validation selection: 142 passed.
- Full backend: 386 passed, 4 environment-gated skips; 81% total coverage. Compileall and Ruff
  lint/format passed. Changed passport modules pass Mypy; repository application Mypy retains 42
  pre-existing errors in unrelated files.
- Bandit: zero findings. pip-audit: no known vulnerabilities; unpublished local package skipped.
- Frontend: clean install, lint (0 errors/1 known warning), typecheck, 11 files/27 tests, build, and
  production audit (0 vulnerabilities) passed.
- Docker Compose config, backend image build, and PostgreSQL Alembic drift check passed.
- No consumed grounding holdout or browser E2E was run.

## Verifiable Answer Passport Phase 2 — 2026-08-02

Focused Phase 1/2 passport tests cover immutable projections, server-derived scope and document
metadata, exact displayed mappings, extractive/Ollama metadata, disabled/no-signer behavior,
supported/refused/conflict/error/cancelled states, concurrent at-most-once issuance, cancellation,
sanitized signer failure, minimal audit metadata, cross-scope substitution and offline verification.

Full backend, frontend, Docker, Alembic and security results are recorded in `VALIDATION_REPORT.md`.

| Gate | Result | Evidence |
|---|---|---|
| Focused passport | Pass | 117 tests across Phase 1 core/CLI/matrix and Phase 2 issuance |
| Backend | Pass | 342 passed, 4 environment-gated skips; 80% coverage |
| Issuance coverage | Pass | 92% (`app/passport/issuance.py`) |
| Formatting/lint | Pass | compileall and Ruff over `app tests` |
| Typing | Scoped pass | issuance module has zero Mypy errors; repository run reports 42 pre-existing errors in untouched modules |
| Security | Pass | Bandit zero findings; pip-audit no known vulnerabilities |
| Frontend | Pass | lint (0 errors/1 known warning), typecheck, 11 files/27 tests, production build |
| Frontend audit | Pass | 0 production vulnerabilities |
| Docker/migrations | Pass | Compose config, backend/frontend/ingestion-worker build, Alembic no new operations |
| Browser E2E | Pass | default 1 passed/8 skipped; agentic 5 passed/4 skipped |

## Verifiable Answer Passport Phase 1 — 2026-08-01

Overall release gates: **PASS**.

| Area | Result | Evidence |
|---|---|---|
| Focused passport matrix | Pass | 99 tests: canonicalization, independent Ed25519/JWS interoperability, hashes, synthetic eligibility, snapshots, lifecycle, all status-to-exit mappings, mutations, precedence and socket blocking |
| Backend full suite | Pass | 324 passed, 4 environment-gated skips, 0 failures |
| Backend coverage | Pass | 80% total; passport package 526/561 statements, approximately 94% |
| Compile / Ruff | Pass | Compileall; Ruff lint and format over `app tests` |
| Mypy | Scoped pass | `app/passport` passes; repository-wide configured run exposes 29 pre-existing errors in untouched modules |
| Security | Pass | Bandit: zero findings; pip-audit: no known vulnerabilities |
| Frontend | Pass | lint: 0 errors/1 previously recorded Fast Refresh warning; typecheck; 11 files/27 tests; production build |
| Frontend audit | Pass | `npm audit --omit=dev`: 0 vulnerabilities |
| Docker | Pass | Compose config and current-source backend image build |
| Schema drift | Pass | Docker PostgreSQL `alembic check`: no new upgrade operations |
| CLI | Pass | module and installed `ekip-vap` forms, text/JSON, stable exit codes, malformed/missing/oversized input, explicit symlink behavior |

Canonicalization is classified as a **restricted RFC 8785-compatible profile** for the tested
supported JSON domain. Eight stable canonical vectors cover ordering, nesting, arrays, Unicode,
escapes, equivalent field order and integers; fractional/exponent and non-finite numbers are
rejected. The protected mutation/attack vectors were detected or deterministically classified.

The independent audit added 25 tests. It classifies the envelope as RFC 7515 Appendix F standard
encoded detached JWS, not RFC 7797, and verifies interoperability in both directions with an
independent Base64URL/JSON/PyCA path. The CLI maps only `VERIFIED` to exit `0`; review-required
statuses map to exit `2`; invalid, revoked, malformed and input-failure outcomes map to exit `1`.

No consumed grounding holdout was executed. Existing full-suite tests confirmed one-pass Agent
retrieval, neutral refusal, supported answers, conflicts, tenant isolation, support threshold
`0.72`, and Agent retry budget `0` remain unchanged.

Validated on 2026-07-23 from branch `release/v0.2.1-operational-hardening`.

## v0.2.1 Operational Hardening Results

| Area | Test | Result | Evidence |
| --- | --- | --- | --- |
| Backend | Full pytest | Pass | `117 passed, 2 skipped` |
| Backend | Coverage | Pass | `76%` total coverage |
| Backend | Ruff | Pass | `ruff check app tests`; `ruff format --check app tests` |
| RAG | Deterministic demo-topic regression | Pass | `Topic: Functions` answers `What is the demo topic?` in Standard Search and Controlled Agent without LLM/Ollama |
| RAG | Non-conflict heading/value regression | Pass | Tutor qualification and teaching method do not conflict with demo topic |
| RAG | Genuine topic conflict regression | Pass | `Functions` versus `Trigonometry` returns confirmed conflict with abstention |
| Evaluation | Normalized value match | Pass | Expected `Functions` matches actual `The demo topic is Functions.` when evidence and citation are valid |
| Frontend | Evaluation reset regression | Pass | Controlled form state avoids null `.reset()` and retains fields on failure |
| Frontend | Lint/typecheck/test/build | Pass | 1 existing lint warning; typecheck passed; `9` Vitest files and `24` tests passed; Next build passed |
| Frontend | Default Playwright | Pass | `1 passed, 4 skipped` with default disabled flags |
| Frontend | Enabled Playwright | Pass | `5 passed` with agentic/research flags enabled through Docker |
| Security | Audits | Pass | Bandit no issues; pip-audit no known vulnerabilities; npm audit 0 vulnerabilities |
| Docker | Compose and Alembic | Pass | default/observability/web-search config passed; `alembic upgrade head`; `alembic check`: no new operations |
| Runtime | Outage/restart validation | Pass | Redis dispatch outage, MinIO export outage, backend restart, report-worker restart, ingestion-worker restart, PostgreSQL interruption, cancellation, and idempotency all recovered safely |
| Runtime | Tenant isolation | Pass | Cross-scope document/research/artifact/agent-run access returned 403/404 without leakage |
| Runtime | Live SearXNG | Pass | `/agent/query` explicit opt-in returned 5 external evidence items, 4 citations, provider `searxng` |
| Observability | Prometheus/Grafana/OTel | Pass | Prometheus targets up; Grafana API returned `EKIP Agentic Runtime`; OTel collector logged 1 trace batch |
| Load | 5/10/20-user probes | Pass | 100% success; p99 211.8 ms / 374.8 ms / 851.9 ms |

| Area | Test | Result | Evidence |
| --- | --- | --- | --- |
| Backend | Compilation | Pass | `.venv/bin/python -m compileall app tests` |
| Backend | Ruff lint | Pass | `.venv/bin/ruff check app tests` |
| Backend | Ruff format | Pass | `.venv/bin/ruff format --check app tests` |
| Backend | Unit/integration/security tests | Pass | `116 passed, 2 skipped` |
| Backend | Coverage | Pass | `76%` total coverage |
| Database | Alembic drift | Pass | Docker PostgreSQL `alembic check`: no new upgrade operations |
| Runtime | Docker stack | Pass | Backend, frontend, PostgreSQL, Redis, MinIO, workers, Prometheus, Grafana, and OTel running |
| Runtime | Agent internal RAG | Pass | Docker API probe job `4982e894-bc00-4c54-b069-f79f44f7f71f`, run `20bc2a99-e839-468d-87b6-4d970909f327`, 1 citation, 1 evidence item |
| Runtime | External disabled | Pass | Job `792e40b9-3357-47e7-b0db-5a4d816f5110`; public-disabled run `1db97c59-c459-4765-93ba-a8b03c4cf0ab`; no external access performed |
| Runtime | External deterministic | Pass | Public run `e4271e7e-b199-458e-a217-f4064478cdf6`; deterministic provider, external citation, provenance returned |
| Runtime | Internal preferred | Pass | Run `01a2870f-5ab1-4086-828c-d710c6a84f3c`; no external tool called when internal evidence was sufficient |
| Runtime | Multi-source evidence probes | Pass | Jobs `bd8e3807-6a6c-45e0-84ac-6712b277ce6e`, `7cb907de-fd1c-4d71-b2c7-3521c6d0d556`, `2d41452f-b96c-4728-a84f-10c8ef07f73d`, `4839fd15-1234-4420-b692-10e56d169a2a`; runs `30a13d77-efaf-4cd8-99ec-da772fc5fc2b`, `854fac77-0904-4aaf-b156-abd43c8142df`, `9d7a5e72-f089-4d6b-9ace-54c6f7a0865c`, `08704576-8908-4635-9095-52f57e3bf4cd`, `ef36a0f9-be84-43f0-923a-1ee2b430200b`, `e9896f8c-a078-42f4-94f1-b29a6935493b`, `0c6580ce-c538-4140-b1b6-bbf0266ba6b7`, `c71c9c10-f24e-4b8b-9138-2f43c1820cc0`, `1c591745-b41d-448f-8d8b-e3a50064a8ea`, `30a54d73-9b9d-4914-8179-eed436c7a155` |
| Runtime | Research report worker | Pass | Docker API probe document `d4a0ee81-3247-4cb1-92ca-8b4813589b03`, ingestion job `1985fb7d-2fd7-488b-994a-fa9bf5b0a9b6`, research job `b4653536-ffd1-4132-b513-4bd19680e5dd`, agent run `3593b650-7676-4616-b4fe-9a5d6ad33e5c`, markdown/PDF/DOCX downloads passed |
| Runtime | Completed-task retry | Pass | Same request id, 1 chunk, 1 embedded chunk, no asyncpg/event-loop log matches |
| Runtime | Redis outage recovery | Pass | Upload became `retry_pending`; automatic dispatcher completed it after Redis restart |
| Runtime | Orphan retry jobs | Pass | `0` jobs in `retry_pending` or `dispatch_failed` after recovery |
| Runtime | MinIO outage | Pass | Sanitized 500 and no document row persisted |
| Observability | Prometheus targets | Pass | `backend:8000`, `ingestion-worker:9101`, `evaluation-worker:9102`, `report-worker:9103` all `up=1` |
| Observability | Worker metrics | Pass | `ekip_worker_tasks_completed_total{worker_role="ingestion"} = 4` |
| Frontend | Lint | Pass | 0 errors, 1 existing Fast Refresh warning |
| Frontend | Typecheck | Pass | `npm run typecheck` |
| Frontend | Unit/component tests | Pass | 9 files, 24 tests passed |
| Frontend | Browser E2E | Pass | 1 Playwright Chromium spec passed with default flags; gated deterministic agentic Docker run passed 5 Chromium specs |
| Frontend | Build | Pass | `npm run build` |
| Frontend | Agentic workspace | Pass | `/agent`, `/agent/runs/{run_id}`, `/agent/research`, `/agent/research/{job_id}` build and render behind disabled-by-default feature flags |
| Runtime | Agentic frontend Docker E2E | Pass | With backend/frontend agentic flags enabled, Playwright validated registration, upload, agent query, async research creation, `/search` route visibility, and cleanup through PostgreSQL/Redis/MinIO/Celery |
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
| Agent | Evidence normalization | Pass | Internal, SearXNG, Wikipedia, arXiv, and approved API normalization tests passed |
| Agent | Deduplication | Pass | External URL duplicates merge; cross-tenant internal evidence never merges |
| Agent | Rank fusion | Pass | Deterministic reciprocal-rank fusion preserves internal priority for org questions |
| Agent | Context budget | Pass | Evidence cap/truncation preserves citation labels |
| Agent | Claim verification | Pass | Supported, partially supported, unsupported, and conflicted claim paths tested |
| Agent | Conflict detection | Pass | Numeric, date, and owner/entity contradiction tests passed |
| Agent | Citation validation | Pass | Unknown/unrelated citation labels are rejected |
| Agent | Deterministic synthesis | Pass | Grounded extractive synthesis and unsupported-claim removal tested |
| Evaluation | Multi-source metrics | Pass | Fixture metrics computed: support rate 0.5, precision 1.0, recall 0.75 |
| Agent | Cancellation | Pass | Cancelled orchestrator run persisted as `cancelled` |
| Research | Targeted backend tests | Pass | Included in full backend suite; direct targeted run also passed 12 tests |
| Research | Feature flag and lifecycle | Pass | Disabled response, async job creation, status read, artifact listing, signed downloads |
| Research | Report cases | Pass | Simple supported question, knowledge absence, conflicting evidence, cancellation, idempotency, cross-tenant denial, cross-workspace document denial |
| Research | Exports | Pass | Markdown contains grounded answer; PDF starts `%PDF`; DOCX starts `PK` |
| Research | Citation validation | Pass | Report stores verified citation count and citation metadata from controlled agent response |
| Research | Existing search regression | Pass | `/api/v1/search` unchanged in research integration test |
| Regression | Existing search endpoint | Pass | `/api/v1/search` still returns answer and retrieval diagnosis |
| Migration | Agent tables | Pass | Disposable SQLite Alembic `upgrade head` reached `c8f4a2d91b77` |
| Docker | Smoke | Pass | `docker compose config`; rebuilt backend and frontend images; observability stack healthy |
| Docker | Web-search profile | Pass | `docker compose --profile web-search config` |
| Observability | Agent metrics | Pass | All requested agent metric families exposed without sensitive labels |
| Observability | Alerts and dashboard | Pass | `docker compose --profile observability config`, Prometheus ready, backend `/metrics` exposed agent metrics |
| Runtime | Load probe | Pass | 5/10/20-user local probes all 100% success; max observed p99 599.1 ms |
| Runtime | Worker restart resilience | Pass | `report-worker` restarted and returned healthy |
| Optional | SearXNG profile | Pass/Partial | Internal container healthy and `/healthz` returned `OK`; startup logs show default live-engine warnings |
| Optional | Ollama profile | Partial | CLI available with `tinyllama:latest` and `llama3:latest`; generation was not run |

## Notes

- `npm run test` initially collected `tests/e2e/runtime.spec.ts`; `vitest.config.ts` now excludes `tests/e2e/**`.
- `npm audit --omit=dev` identified vulnerable transitive `sharp <0.35.0`; a targeted `sharp@0.35.3` override was applied instead of the audit-suggested breaking Next downgrade, and the audit now reports 0 vulnerabilities.
- Host-side API and browser validation required sandbox escalation to reach Docker-published localhost ports.
- Agentic frontend Docker runtime validation passed through PostgreSQL/Redis/MinIO/Celery with feature flags enabled for the probe.
- Next.js was upgraded to `16.2.11`; `npm audit --omit=dev` now reports 0 vulnerabilities.

## Phase 2 Test Results — 2026-07-28

- Backend: 157 collected; 153 passed and 4 skipped. The opt-in live model checks were
  skipped because no operator-provisioned model was available.
- Coverage: 76%.
- Frontend: 10 files, 28 tests passed.
- Playwright default: 1 passed, 4 gated skipped.
- Playwright deterministic agentic profile: 5 passed.
- Backend, frontend, ingestion, evaluation, and report-worker images built; all affected
  services were healthy after restart.
- Alembic upgrade and drift check passed.
- Live local model: unavailable, not downloaded, result `PARTIAL`.

## Phase 2 live-model test results — 2026-07-28

The opt-in live tests passed cache-only with network-offline flags. The 14-document,
9-query safe corpus produced:

| Mode | Recall@1/3/5 | MRR | nDCG@5 | Avg / p50 / p95 ms |
|---|---|---:|---:|---:|
| Lexical | .9375 / .9375 / .9375 | 1.0000 | .9516 | .196 / .187 / .291 |
| Deterministic hybrid | .9375 / .9375 / 1.0000 | 1.0000 | .9813 | .289 / .288 / .312 |
| Live semantic hybrid | .9375 / .9375 / 1.0000 | 1.0000 | .9813 | 7.743 / 7.530 / 9.439 |
| Live semantic + reranker | .8125 / 1.0000 / 1.0000 | .9375 | .9539 | 17.621 / 16.817 / 21.100 |

Every mode measured citation precision .8000, citation recall .8889, answer support
.8750, unsupported-claim rate .2222, recovery 1.0000, tenant isolation 1.0000, and
knowledge-absence accuracy .0000. Raw safe results are in
`docs/evaluation/phase2-live-results.json`; re-index and failure matrices are adjacent.

Regression totals: backend 155 passed/4 skipped with 76% coverage; frontend 28/28;
Bandit zero findings; pip-audit no known vulnerabilities; npm production audit zero.
Docker builds, health, Alembic upgrade and drift check passed. A first Chromium launch
was denied by the macOS sandbox and passed on the permitted retry.

## Phase 2 calibration tests

- Benchmark: 60 development queries and 40 untouched holdout queries.
- Backend: 158 passed, 4 expected skips; 77% coverage.
- Frontend: 28 passed; lint had zero errors/one existing warning; typecheck and build
  passed.
- Ruff, compileall, Bandit, pip-audit and npm production audit passed.
- New deterministic coverage includes intent classification, revenue/budget hard
  negative, low-quality rejection and incomplete composite rejection.
- Safe aggregate output: `docs/evaluation/phase2-calibration-results.json`.

## Blind acceptance closure

- Pre-registered blind fixture: 120 queries, 15 categories × 8.
- Fixture checksum:
  `16dc10caf8b9608d60abf84f13e6c783d94fbf50bf208d4483840003dbb4a807`.
- Execution count: exactly 1.
- Denominators: 120 total, 96 positive retrieval, 8 absence, 8 isolation, 8 hard
  negative; recovery metric evaluated all 96 positives, of which 40 were marked
  recovery.
- Backend: 158 passed, 4 gated; coverage 76%.
- Frontend: 28 passed; lint/typecheck/build passed.
- Playwright isolated default: 1 passed/5 gated. Isolated agent profile:
  5 passed/1 gated.
- Docker isolated build/up, Alembic upgrade/check, Bandit, pip-audit and npm audit
  passed. The isolated project and volumes were deleted.
# Phase 2B retrieval quality

The 127-query development set compared all-MiniLM-L6-v2/L6 against
BGE-small-en-v1.5/L6. Both produced hard-negative Recall@1 1.0000 and overall
Recall@1 0.9346; BGE had higher steady-state latency and peak RSS, so the
predeclared selection policy retained the current pair. The 160-query blind
result is recorded in `docs/evaluation/phase2b-blind-holdout-v1-results.json`.

Regression closure: backend 165 passed/4 environment-gated skipped with 77%
coverage; Ruff, formatting, compileall, Bandit, and pip-audit passed. Frontend
lint had one pre-existing Fast Refresh warning and no errors; typecheck, 28
Vitest tests, production build, and npm audit passed. The isolated 15-case
Chromium acceptance passed, as did the real-stack runtime Playwright test
against the disposable Docker project. A broad agentic-flag run against an
older process on ports 3000/8000 was not a valid isolated run (feature-build
mismatch and stale retrieval data); the relevant agent workspace test passed,
while three accessibility cases and the runtime case failed in that mismatched
environment. Docker builds, service health, Alembic upgrade/check, and
disposable-volume cleanup passed.

# Phase 2B agentic Playwright closure

The prior four failures were diagnosed as follows:

| Tests | Expected | Historical actual | URLs/process | Evidence-based classification |
| --- | --- | --- | --- | --- |
| responsive desktop/tablet/mobile | agent form visible with controlled agent flag enabled | `agent-form` absent | default `http://localhost:3000`; frontend was an older developer process compiled with the public agent flag off; mocked backend routes were not reached for the initial assertion | frontend feature/build mismatch |
| runtime registration/search/isolation | the run-scoped Atlas document supports the compound answer | insufficient-evidence response | default frontend `http://localhost:3000`, API `http://localhost:8000/api/v1`; normal developer stack, not the disposable ports | unidentified backend/runtime mismatch; no stale-document claim is made |

The historical processes exposed no build identity, so their Git commit was
not safely derivable. The test fixtures themselves used timestamp-scoped
organizations, workspaces, users, and filenames with fresh browser storage.

Final isolated results:

- default profile: 1 passed, 6 intentional feature-gated skips
- agentic profile: 5 passed, 2 intentional semantic/Phase-2B skips
- responsive agentic checks: 3/3 passed within the agentic profile
- Phase 2B 15-case Chromium profile: 1 passed
- production Next.js build against the isolated backend: passed in every
  profile

The preflight verified commit `c5b6e68dc247528274dfbe1b8f12c30b3d0dafde`,
compatibility `ekip-e2e-v1`, intended alternate URLs, backend readiness, and
matching feature flags before test execution. The blind benchmark was not
executed or changed. Final backend regression: 166 passed, 4 environment-gated
skips, 77% coverage; Ruff, format, compileall, Bandit, and dependency audits
passed. Frontend lint had no errors and one existing Fast Refresh warning;
typecheck, 29 Vitest tests, production build, and dependency audit passed.

# Pre-Ollama response-state results

- Canonical invariant/claim-normalization matrix: 12 passed.
- Focused Agent, evidence, diagnosis, Evaluation, and Research tests: passed.
- Full backend: 178 passed, 4 environment-gated skips, 78% coverage.
- Frontend typecheck: passed.
- Frontend Vitest: 29 passed.
- Frontend lint: no errors; one existing Fast Refresh warning.
- Isolated Chromium: default 1 passed/6 gated skips; agentic 5 passed/2
  gated skips; response-state profile 1 passed across 18 states.
- Docker builds and Compose config passed; Alembic upgrade/check reported no
  pending operations in every disposable profile.
- Full-stack results are recorded in the final acceptance report for
  `fix(rag): enforce response and conflict consistency`.
# Ollama grounded-generation tests (2026-07-30)

The dedicated backend suite contains 20 passing cases covering disabled defaults, SSRF
and model allowlists, prompt injection, schema strictness/no reasoning, hallucinated
evidence IDs, numeric/entity/negation/equation checks, server citation reconstruction,
safe extractive fallback, and circuit recovery. Full backend: 200 passed, 4 gated skips,
78% coverage. Frontend: 31 passed; lint (one pre-existing warning), typecheck, and build
passed. Isolated Chromium: 1 applicable passed, 6 feature-gated skipped. Docker images
built and Alembic upgrade/check passed. Bandit passed; pip-audit and npm audit found no
known vulnerabilities.

Live closure: backend 201 passed / 4 live-gated skipped, coverage 78%; frontend 31
passed. Live Ollama isolated Chromium passed 1/1 applicable test (6 feature-gated
skips). Agentic isolated Chromium passed 5 with 2 feature-gated skips. Docker builds and
Alembic upgrade/check passed. Bandit passed; pip-audit and npm audit found no known
vulnerabilities.

Grounded v2 closure: backend 208 passed / 4 live-gated skipped, 78% coverage;
frontend 31/31 passed, production build and typecheck passed. Bandit and pip-audit
passed; production `npm audit --omit=dev` reported zero vulnerabilities (the full
development-tree install reported one high-severity advisory). Docker images built
and Alembic upgrade/check reported no pending operations.

The isolated live-Ollama Chromium safety regression completes with known allowed
fail-closed outcomes, but acceptance remains partial: the Search layer rejected the
equation response and omitted a citation on one correct negation response. Disposable
Compose projects, networks, PostgreSQL, Redis, MinIO volumes, traces, and screenshots
are removed by the profile trap.

# Verifiable Answer Passport Phase 3A (2026-08-02)

- Focused lifecycle/trust/issuance: 40 passed.
- Full backend: 364 passed, 4 environment-gated skips; total coverage 81%.
- New lifecycle and trust-bundle modules: 89% and 88% coverage; issuance: 92%.
- Compileall and Ruff check/format: passed. Changed-module Mypy: passed.
- Repository Mypy: 42 pre-existing errors in 26 unchanged files; no new-module error.
- Bandit: zero findings. pip-audit: no known vulnerabilities (local package skipped).
- Frontend: 11 files/27 tests passed; typecheck/build passed; lint zero errors and one
  inherited Fast Refresh warning; production npm audit zero vulnerabilities.
- Docker Compose config and clean backend/frontend/ingestion-worker builds passed. Alembic
  reported no new upgrade operations.
- Default isolated Chromium: 1 passed, 8 accurately gated skips. Agentic/Research/accessibility:
  5 passed, 4 accurately gated skips. Disposable profile resources were removed by traps.
- Consumed grounding holdouts were not executed. Threshold `0.72`, Search one-pass/no-retry
  behavior, and Agent retrieval retry budget `0` remain unchanged.

# Verifiable Answer Passport Phase 4 (2026-08-02)

- Focused backend frontend-contract suite: 8 passed; full backend: 410 passed and 4
  environment-gated skips; total coverage 81%.
- Compileall, Ruff check/format, and Bandit passed. Repository Mypy retained the same 42
  pre-existing errors in 26 files; no new Phase 4 argument/type error remained.
- pip-audit found no known vulnerabilities (the local package was skipped).
- Frontend clean install completed; 13 files/47 tests passed. Typecheck and production build
  passed. Lint reported zero errors and one inherited Fast Refresh warning.
- Production npm audit found zero vulnerabilities.
- The isolated passport Chromium journey passed 1/1. The default profile passed 2 with 8
  accurate feature-gated skips; Agent/Research/accessibility passed 6 with 4 accurate skips.
- Compose configuration, clean backend/frontend/ingestion-worker image builds, Alembic upgrade,
  and Alembic no-pending-operations checks passed in disposable projects.
- No consumed grounding holdout was executed. Threshold `0.72`, Search one-pass/no-retry,
  Agent retry budget `0`, and the server feature defaults remain unchanged.

# Search/browser acceptance closure (2026-07-31)

- Focused backend/API equation, obligation-citation, and owner/date coverage: 30 passed.
- Full backend: 215 passed, 4 environment-gated skipped; coverage 78%.
- Compileall, Ruff check/format, and Bandit: passed.
- Frontend: 34 passed; lint had no errors and one existing Fast Refresh warning;
  typecheck and production build passed.
- Default isolated Chromium: 1 passed, 7 feature-gated skipped.
- Agentic isolated Chromium: 5 passed, 3 feature-gated skipped.
- Live Ollama isolated Chromium: 1 passed, exercising seven strict answer/citation
  cases plus fallback, scope, isolation, and responsive acceptance.
- Alembic upgrade/check: passed with no pending operations in each isolated runtime.
- pip-audit and production npm audit: no known vulnerabilities.
- The consumed v1 and 140-case v2 holdouts were not run.

# Enterprise release hardening (2026-07-31)

- Corpus generator/manifest contract: 100 documents; passed deterministic verification.
- Acceptance matrix contract: 118 cases; all required fields and unique IDs verified.
- Enterprise upload: 100 accepted, zero synchronous upload failures.
- Enterprise ingestion: 100 completed, zero failures/timeouts; average 171.99 ms,
  p50 269.21 ms, p95 320.10 ms.
- Extraction: 50 GOOD, 10 ACCEPTABLE, 40 intentionally LOW_QUALITY code/config files.
- Scoped Search: 30/30 safe canonical responses; average 25.98 ms, p50 24.33 ms,
  p95 39.28 ms, p99 71.08 ms. The final query-selection refinement awaits a quota-blocked
  rerun; the recorded distribution was 24 supported and 6 safe insufficient responses.
- Tenant selection: authorized 200, cross-tenant 404, zero exposures.
- Enterprise Chromium: 1/1 passed across desktop/tablet/mobile with no console error or
  horizontal overflow.
- Two-minute concurrency: 12,930 requests, 8,620/8,620 health 200s, 120 admitted Search
  200s, 4,190 expected 429s, zero unexpected errors/5xx; overall p95 243.32 ms.
- Soak: 1,200 seconds, 28,950 requests, 19,300/19,300 health 200s, 1,190 admitted
  Search 200s, 8,460 expected 429s, zero unexpected errors/5xx; overall p95 25.34 ms.
- Resource trend: backend 117.4→117.2 MiB; workers stable; PostgreSQL connections 11,
  Redis clients 35/three blocking workers, queues empty at sampled checkpoints.
- Backup/restore: counts matched `4,4,100,460`; downgrade/upgrade/check and private MinIO
  inspection passed.
- Full backend: 218 passed, 4 environment-gated skipped, 78% coverage; Ruff, format,
  compileall, and Bandit passed.
- Frontend: 34 passed; typecheck/build passed; lint had zero errors and one existing warning.

## Closure reruns (2026-08-01)

- Search refinement: 30/30 passed; 24 supported and 6 safe insufficient-evidence states.
- Default Playwright: 1 passed, 8 accurately gated skips.
- Agentic/Research/accessibility Playwright: 5 passed, 4 unrelated gated skips.
- Live Ollama Playwright: 1 passed using the required version, model, and digest.
- Enterprise operational/browser: recovery probes passed; enterprise Chromium 1 passed.
- Semantic hybrid: Recall@1 `.9375`, Recall@5 `1.0`, support `.875`, unsupported `.2222`,
  absence accuracy `0.0`; release acceptance failed.
- Semantic plus reranker: Recall@1 `.8125`, Recall@5 `1.0`, support `.875`, unsupported
  `.2222`, absence accuracy `0.0`; release acceptance failed.
- Backend: 218 passed, 4 environment-gated skipped; coverage 78%; compileall/Ruff passed.
- Frontend: 34 passed; typecheck/build passed; lint zero errors and one inherited warning.
- Bandit: zero findings. pip-audit and production npm audit: zero known vulnerabilities.
- The v1/v2 consumed grounded-generation holdouts were checksum/counter inspected only.

## Final semantic and release closure (2026-08-01)

- Semantic hybrid: 8/8 supported cases complete; 1/1 absence correct; unsupported 0/9;
  citation precision/recall 1.0000; Recall@1 `.9375`, Recall@5 `1.0000`; selected-document
  and tenant isolation 1.0000.
- Semantic plus reranker: 8/8 supported cases complete; 1/1 absence correct; unsupported
  0/9; citation precision/recall 1.0000; Recall@1 `.9375`, Recall@3/5 `1.0000`; unique
  materials hard positive rank 1.
- Focused semantic safety regressions: 16 passed; full backend: 221 passed, 4 gated skips,
  78% coverage. Compileall, Ruff check/format, Bandit, and pip-audit passed.
- Frontend: 34 passed; typecheck and production build passed; lint zero errors/one existing
  warning; production npm audit zero vulnerabilities.
- Default Chromium: 1 passed/8 gated skips. Agentic/Research/accessibility: 5 passed/4
  gated skips. Enterprise Chromium: 1 passed. Live Ollama Chromium: 1 passed.
- Operational correlation and audit coverage passed for all requested actions; prohibited
  private audit payload terms: 0.

## Grounding assurance partial result (2026-08-01)

- Corpus: 300 fictional document records; suite: 1,350 cases; development: 450; blind: 900.
- New blind holdout: consumed once, checksum
  `d090a6e007de9c385ca0b5563e716f5382bb1e5e09051ad46cdd66baa3d50f5a`.
- Blind distribution: 0 answered, 900 refused, 0 conflict. Refusal accuracy 1.0000;
  unsupported visible claims, unauthorized citations, scope leaks, and post-insufficiency
  adaptive actions all 0.
- Claim/citation/conflict metrics are not reportable because their denominators are zero.
  Overall status is PARTIAL PASS; the consumed holdout was not rerun.

## Grounding Assurance v2 result (2026-08-01)

- Independent corpus: 540 documents in 180 families; 450 development and 900 blind cases.
- Blind denominators/results: 360 supported, 405 refused, 135 conflict; all passed.
- Claim and citation precision/recall: 1.0000. Refusal accuracy and conflict precision/
  recall: 1.0000. False-conflict rate: 0.
- Every critical fact category: 1.0000. Mutation and evidence-ablation assurance: 1.0000.
- Unauthorized/unsupported claims and citations, tenant/selected-scope leakage, diagnosis
  leakage, adaptive attempts, post-insufficiency reformulations, and Top-K changes: 0.
- Backend: 225 passed, 4 gated skips, 79% coverage. Frontend: 27/27 passed, typecheck/build,
  zero lint errors/one inherited warning. Default, Agent/Research/accessibility, live Ollama,
  semantic, and reranker profiles passed.
