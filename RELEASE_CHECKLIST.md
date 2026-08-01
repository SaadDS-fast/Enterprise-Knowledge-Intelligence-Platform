# Enterprise release checklist

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
