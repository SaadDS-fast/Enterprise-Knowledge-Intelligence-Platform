# Enterprise release checklist

## Verifiable Answer Passport Phase 3B

- [x] Flags default false; no production signer or private configuration.
- [x] Migration upgrade, downgrade, re-upgrade, single head, and mutation trigger pass.
- [x] Scoped persistence/idempotency and metadata/export authorization tests pass.
- [x] Corrupt denial, forensic status, fixed package, and public-only trust tests pass.
- [x] Backend, frontend, Docker, Bandit, pip-audit, and npm audit pass.
- [x] No evidence/private material, frontend workflow, AWS change, holdout, push, or tag.

## Verifiable Answer Passport Phase 3A

- [x] Immutable checksummed PENDING/ACTIVE/RETIRED/REVOKED metadata and strict transitions.
- [x] Zero-or-one active key, irreversible revocation, non-reusable IDs, historical retention.
- [x] Atomic in-memory rotation and server-side Phase 2 resolved signer.
- [x] Deterministic public-only lifecycle bundles, chaining, rollback checks, optional anchor.
- [x] Trust bootstrap and Phase 3B production prerequisites documented.
- [x] No API, migration, frontend, production key provider, private-key config, or AWS/KMS work.
- [x] Record complete Phase 3A backend/frontend/E2E/Docker/security validation below.
- [x] Commit only after every mandatory gate passes; never push, merge, or tag in this task.

## Verifiable Answer Passport Phase 2

- [x] Internal hook occurs only after canonical answer finalization.
- [x] `ANSWER_PASSPORT_ENABLED` defaults to `false`.
- [x] Disabled and missing-signer paths produce no artifact.
- [x] Refusal, conflict, error, cancellation and incomplete mappings are ineligible.
- [x] Projection scope/version/checksum data is server-derived.
- [x] Issuance failure leaves the answer and citations unchanged.
- [x] No public API, migration, frontend workflow, persistence, evidence export or production key.
- [x] Phase 1 offline verifier and CLI dependency boundary remains intact.
- [x] Complete backend/frontend/Docker/security validation and record final counts.

Proposed release: `v0.3.0-enterprise-rc1` (not created). Baseline/rollback:
`736a402`.

- [x] Synthetic corpus and acceptance matrix are versioned and reproducible.
- [x] Consumed grounded-generation holdouts remain unchanged and locked at `1/1`.
- [x] Safe feature defaults and local-only Ollama controls are preserved.
- [x] Backend, frontend, security, Docker, migration, and isolated browser checks run.
- [x] Tenant and selected-document denial paths expose no data.
- [x] Disposable Compose data is removed after every profile.
- [x] Rerun corrected operational/default/agentic/live profiles and dependency audits.
- [x] Close the semantic and semantic-plus-reranker acceptance failure recorded in
  `VALIDATION_REPORT.md` using development-only work and a permitted future evaluation.
- [x] Demonstrate request-ID correlation and the complete safe audit-event matrix.
- [ ] Create the requested hardening commit after final artifact and secret review.
- [ ] Tag only through a separately authorized release action; this task does not tag.

Never place secrets, private documents, runtime databases, model files, raw prompts,
provider output, traces, screenshots, or load logs in a release commit.

## Grounding assurance

- [x] Preserve grounded-generation v1/v2 consumed registrations.
- [x] Freeze and execute grounding-assurance holdout once.
- [x] Record the frozen partition defect without rerunning or retuning.
- [x] Obtain non-vacuous v2 blind supported-answer, citation, and conflict denominators.
- [x] Pass v2 preflight and consume the independently frozen holdout exactly once.
- [x] Preserve v1 unchanged as the refusal-only historical evaluation.
- [x] Complete final artifact and secret review before the grounding-assurance commit.
