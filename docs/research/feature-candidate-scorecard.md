# Thesis-safe feature candidate scorecard

Status: proposed, 2026-08-01. No feature is implemented by this document.

## Scoring method

Scores are 1 (unfavorable) to 5 (favorable). For operational cost, security risk,
thesis-overlap risk, overlap with the existing platform, research saturation, and market
saturation, **5 means low burden/risk/saturation or a complementary fit**. The unweighted total
is a decision aid, not a proof. All candidates are constrained to operate without post-failure
retrieval changes or failure diagnosis.

Abbreviations: MD differentiation, EV enterprise value, TD technical depth, PD portfolio demo,
SF single-developer feasibility, DT deterministic testability, OC operational-cost favorability,
SR security-risk favorability, TR thesis-safety, EP complementary platform fit, RS low research
saturation, MS low market saturation.

| Candidate | MD | EV | TD | PD | SF | DT | OC | SR | TR | EP | RS | MS | Total / 60 | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A. Verifiable Answer Passport and Offline Audit Replay | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 3 | 5 | 5 | 4 | 5 | **55** | Select for proposed ADR |
| B. Answer validity expiry and evidence freshness monitoring | 3 | 4 | 3 | 4 | 4 | 5 | 4 | 4 | 5 | 4 | 3 | 3 | 46 | Reject as standalone; optional later passport policy |
| C. Document-change impact on previously issued answers | 4 | 5 | 5 | 5 | 2 | 4 | 3 | 3 | 4 | 4 | 3 | 4 | 46 | Reject for first release; high scope and inference risk |
| D. Evidence-backed policy comparison workspace | 2 | 5 | 4 | 5 | 3 | 4 | 3 | 4 | 5 | 3 | 2 | 2 | 42 | Defer; valuable but saturated and workflow-heavy |
| E. Compliance evidence-package generation | 3 | 5 | 3 | 4 | 4 | 5 | 4 | 3 | 5 | 4 | 3 | 3 | 46 | Defer; compose later from passports |
| F. Grounded Decision Ledger | 4 | 5 | 4 | 5 | 3 | 5 | 4 | 3 | 5 | 4 | 4 | 4 | 50 | Runner-up; requires governance workflow choices |

## Score explanations

### A. Verifiable Answer Passport and Offline Audit Replay

- **MD 5:** the reviewed official pages commonly document citations/audit, but not this portable,
  signed, offline-verifiable combination.
- **EV 5:** auditors, reviewers and regulated operators can verify integrity without trusting the
  live application.
- **TD 5:** canonicalization, signatures, scoped manifests, version semantics and replay make a
  substantial systems feature.
- **PD 5:** answer modification, citation modification and stale-snapshot demos are immediate and
  legible.
- **SF 4:** a focused CLI/API/UI slice is realistic, though secure key lifecycle work is material.
- **DT 5:** fixtures, hashes and signature outcomes have exact expected results without an LLM.
- **OC 4:** hashing and signing are inexpensive; HSM/KMS operations can be optional deployment
  hardening.
- **SR 3:** evidence export, signing authority and metadata leakage require careful controls.
- **TR 5:** it runs only after a supported answer and cannot retrieve, retry or diagnose.
- **EP 5:** it consumes existing claims, citations, versions, checksums and audit identities.
- **RS 4:** adjacent provenance/attribution work exists, but the bounded scan found limited direct
  treatment of portable answer certificates.
- **MS 5:** the combination was not commonly documented in the reviewed vendor sources.

### B. Answer validity expiry and evidence freshness monitoring

- **MD 3:** validity windows and freshness indicators are established governance concepts.
- **EV 4:** time-sensitive policy consumers need to know when review is due.
- **TD 3:** clocks, policies and status calculation are meaningful but conventional.
- **PD 4:** a deterministic before/after expiry demonstration is clear.
- **SF 4:** scheduled metadata checks and UI status are tractable.
- **DT 5:** frozen clocks and version fixtures produce exact outcomes.
- **OC 4:** scheduled checksum/version checks are modest if bounded.
- **SR 4:** read-only metadata comparison has limited privilege; notification routing adds exposure.
- **TR 5:** safe when status never triggers search or explains weak support.
- **EP 4:** version metadata exists, but historical answer records need a durable representation.
- **RS 3:** temporal and version-aware QA are active research areas.
- **MS 3:** freshness and lifecycle controls are already familiar enterprise features.

### C. Document-change impact on previously issued answers

- **MD 4:** claim/span-level impact visualization is less common than generic version history.
- **EV 5:** policy owners can identify decisions needing human review after source changes.
- **TD 5:** stable span identity, version diffs and affected-claim graphs are challenging.
- **PD 5:** changing one source clause and highlighting impacted issued answers is compelling.
- **SF 2:** robust document alignment and scale make a first release large for one developer.
- **DT 4:** curated diffs are exact, but arbitrary-document alignment is harder to oracle.
- **OC 3:** rehash/diff jobs and reverse indexes add storage and processing.
- **SR 3:** cross-version evidence and historical permissions increase disclosure risk.
- **TR 4:** safe only as post-issuance comparison; any evidence recovery or automatic re-answer is
  prohibited.
- **EP 4:** versions and citations help, but reverse lineage is not currently implemented.
- **RS 3:** temporal and change-aware retrieval research is active.
- **MS 4:** answer-specific impact appears less commonly documented than source freshness.

### D. Evidence-backed policy comparison workspace

- **MD 2:** comparison, summarization and collaborative workspaces are common assistant patterns.
- **EV 5:** legal, HR and compliance users regularly compare policy versions or jurisdictions.
- **TD 4:** aligned claims, applicability and conflict presentation are nontrivial.
- **PD 5:** side-by-side source-backed differences demo well.
- **SF 3:** backend comparison plus a polished workspace is a moderate-to-large solo effort.
- **DT 4:** fixed selected documents allow deterministic comparison fixtures.
- **OC 3:** generation and UI workflows cost more than a post-answer integrity feature.
- **SR 4:** selected-document isolation reduces exposure when preserved.
- **TR 5:** safe if users select documents before one normal pass and no weak-support adaptation
  occurs.
- **EP 3:** existing conflict handling helps, but a new workflow and contracts are required.
- **RS 2:** policy/compliance QA is extensively studied.
- **MS 2:** enterprise assistants already market comparison and summarization workflows broadly.

### E. Compliance evidence-package generation

- **MD 3:** evidence exports are common in GRC, though grounded-answer packaging is narrower.
- **EV 5:** audit teams need repeatable, reviewable evidence collections.
- **TD 3:** template, manifest and authorization design are solid but not algorithmically novel.
- **PD 4:** exporting and validating a regulator-ready package is tangible.
- **SF 4:** bounded templates and immutable manifests are feasible for one developer.
- **DT 5:** fixture packages can be byte-for-byte or schema/signature verified.
- **OC 4:** exports are inexpensive, with storage/retention as the main burden.
- **SR 3:** bundles can concentrate sensitive evidence and require strong export authorization.
- **TR 5:** package only already-supported outputs; never search for missing evidence.
- **EP 4:** citations, audit records and versions supply most inputs.
- **RS 3:** AI governance evidence is an active, established area.
- **MS 3:** governance vendors document evidence and compliance workflows.

### F. Grounded Decision Ledger

An independently identified candidate: an append-only ledger that links a human decision,
approvals and supersession events to an already-supported answer and exact evidence manifest.

- **MD 4:** it joins grounded-answer evidence to accountable human decisions, beyond chat history.
- **EV 5:** regulated teams can answer who approved what, from which evidence, and when.
- **TD 4:** append-only events, signatures, approvals and supersession semantics are substantial.
- **PD 5:** decision creation, approval and tamper detection form a strong end-to-end demo.
- **SF 3:** identity, approval workflow and retention choices broaden the solo scope.
- **DT 5:** event-chain and signature fixtures are deterministic.
- **OC 4:** storage and verification are modest without blockchain.
- **SR 3:** decisions and approver identities are sensitive and retention-heavy.
- **TR 5:** it records only supported outputs and human actions; it performs no retrieval.
- **EP 4:** existing audit and grounding outputs fit, but an append-only decision domain is new.
- **RS 4:** responsible-AI audit work is active; answer-to-decision ledgers are less directly
  saturated in the bounded scan.
- **MS 4:** general audit logs are common, while portable claim/evidence-linked decision records
  were not commonly documented in the reviewed assistant pages.

## Selection

Candidate A is recommended because it has the best combined differentiation, deterministic
testability and fit with existing verified grounding. Candidate F is a plausible later product
layer built on passports. Candidates B and E can become optional lifecycle/export capabilities
after the core artifact is stable. Candidate C is explicitly excluded from the first release;
Candidate D is deferred in favor of a narrower, cheaper and less saturated deliverable.
