# Release Checklist

- Protected tag `v0.1.0-enterprise-mvp` unchanged.
- Safety pre-hardening tag created.
- Backend compile, ruff, format, pytest, coverage, Bandit, and pip-audit passed.
- Frontend npm install/ci, lint, typecheck, unit tests, build, Playwright, and npm audit passed.
- Docker config/build/up, service health, Alembic upgrade/check, logs, and browser E2E passed.
- Agent/research/external flags restored to disabled defaults.
- No secrets, `.env`, signed URLs, generated reports, uploads, databases, volumes, `.next`,
  `node_modules`, or Playwright artifacts committed.
- Release decision recorded as PASS, PARTIAL PASS, or FAIL.

2026-07-23 release decision: **PASS** for mandatory local-first gates. Optional Ollama generation
and live public search quality remain partial/non-blocking checks.
