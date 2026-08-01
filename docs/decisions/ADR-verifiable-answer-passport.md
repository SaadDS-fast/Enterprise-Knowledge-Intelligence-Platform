# ADR: Verifiable Answer Passport and Offline Audit Replay

- Status: **PROPOSED**
- Date: 2026-08-01
- Decision owners: repository maintainers
- Baseline: `3bcc571ed8aa19a01bbb2df7e1cdab51f4ef7651`

## Context

The platform already produces fail-closed, claim-verified answers with exact authorized citations,
versioned documents and audit events. A reviewer who receives an exported answer still lacks a
portable way to determine whether its answer, claims, citations and declared evidence identifiers
were changed after issuance. Vendor products reviewed in
[`market-feature-scan-2026.md`](../research/market-feature-scan-2026.md) commonly document
citations, permissions and audit telemetry, but the reviewed official pages did not commonly
document a portable signed answer plus default-offline evidence verification.

This is a bounded documentation finding, not a claim of global or research novelty.

## Decision

Propose **GroundSeal Passport: Verifiable Answer Passport and Offline Audit Replay** as the next
feature for design review. It will issue a canonical, digitally signed manifest only for an answer
that has already passed the unchanged support gate. A dependency-minimal verifier will validate the
schema, signature, declared content hashes, optional authorized snapshot, versions/configuration,
freshness policy and supplied revocation state without an LLM, retrieval or default network access.

No implementation is authorized by this ADR. Acceptance requires separate review of the detailed
[`specification`](../research/verifiable-answer-passport-spec.md).

## User problem and target users

Auditors, compliance analysts, policy owners, incident reviewers and regulated application teams
need portable evidence that a grounded answer and its citation manifest are the same artifacts that
the platform issued. They should not need live application access or an expensive model to perform
an integrity check.

## Alternatives considered

- **Application audit logs only:** valuable for operators but not portable or independently
  verifiable by a recipient.
- **PDF/JSON export with checksums:** detects accidental corruption only when a trusted checksum
  channel exists; it lacks signer identity and trust policy.
- **Compliance package generator:** useful but should be composed from a stable signed primitive.
- **Grounded Decision Ledger:** strong runner-up, but approval/retention workflows enlarge the first
  implementation.
- **Freshness or document-impact monitor:** useful lifecycle layers; impact analysis is larger and
  risks scope creep into re-answering.
- **Blockchain ledger:** rejected; standard signatures and hashes meet the stated integrity and
  portability goals with less cost and complexity.
- **No selection:** rejected because the bounded evidence supports a useful differentiated
  combination, while retaining explicitly modest claims.

## Differentiation

Approved provisional wording:

> A differentiated combination of verified grounding, portable signed answer evidence, and
> deterministic offline verification; these capabilities were not commonly documented together
> in the official enterprise-assistant pages reviewed as of 2026-08-01.

Evidence: the product table in the market scan records public citations, permissions, histories and
audit capabilities, plus precisely qualified “not found” observations. The research scan shows
strong adjacent work in attribution and RAG evaluation, but is not systematic enough for a research
novelty claim.

## Explicit non-goals and thesis firewall

The passport does not diagnose inadequate retrieval or unavailable knowledge, attribute a failure,
retry, reformulate, change candidate count, select a retriever, expand search, recover evidence,
change a retrieval budget, regenerate an answer, or explain a refusal. Insufficient support remains
a neutral terminal refusal and cannot produce a passport.

The architectural boundary is normative:
[`feature-boundary-vs-thesis.md`](../architecture/feature-boundary-vs-thesis.md). Any proposal that
crosses it is rejected rather than absorbed into this ADR.

## Architecture and security model

An issuance adapter accepts an immutable supported-answer projection. A versioned schema and JSON
Canonicalization Scheme (JCS) produce canonical bytes. Domain-separated SHA-256 hashes bind answer,
claim and evidence representations. Ed25519 signs the manifest through a detached JWS envelope.
Private keys remain in an environment/tenant-scoped KMS/HSM-backed signer in production; the
passport carries only an opaque key ID.

The standalone verifier accepts an explicit trust bundle and optional authorized snapshot. It
reports schema, signature, content integrity, snapshot integrity, scope/configuration match,
revocation and freshness independently. Offline revocation is explicitly limited by trust-bundle
age. A valid signature proves integrity under a key/policy, not factual truth or authorization.

Base artifacts exclude evidence text, prompts, tokens, ACLs and secrets. Evidence export is
separate, explicit, scoped, encrypted and audited. Opaque identifiers and audience fingerprints
reduce metadata disclosure; low-entropy content may require policy-keyed hashes.

## Consequences

Positive:

- strong deterministic testability without an LLM or cloud model;
- visible portfolio demonstration of mutation detection and offline verification;
- reuse of existing claim/citation/version assurance rather than changing retrieval;
- a primitive for later compliance packages, freshness policies and decision ledgers.

Negative:

- new key lifecycle, trust-bundle, migration, retention and export responsibilities;
- cryptographic validity may be misunderstood as truth or current applicability;
- signed identifiers/hashes still create privacy and correlation risks;
- interoperability depends on a rigorously frozen profile and published test vectors.

## Implementation phases

1. Threat model, schema, profile and golden test vectors.
2. Pure canonicalization/signing library and offline CLI.
3. Supported-only issuance adapter, persistence, audit and migration.
4. Export/status APIs and minimal UI.
5. Authorized evidence snapshots, key rotation/revocation and security hardening.
6. Browser/interoperability tests, operator/auditor documentation and external review.

Estimated solo effort is six to nine focused developer-weeks, excluding independent security
review and production KMS procurement/integration lead time.

## Acceptance criteria

- Only an existing supported answer can be issued.
- No issuer/verifier dependency can import or call retrieval, generation or network clients in the
  default path.
- Verification succeeds offline and returns stable machine-readable results.
- Mutations to answer, claim, citation, evidence, manifest or signature are independently detected.
- Signature, trust/revocation, content integrity, authorization/scope and freshness are separate.
- Cross-tenant access fails closed; evidence snapshots require explicit export authorization.
- Rotation supports declared historical verification, and stale revocation data is visible.
- Existing query/API/frontend behavior, support thresholds, refusal semantics and benchmarks remain
  unchanged.

## Evidence required before stronger novelty language

Before any research-novelty statement, complete a registered systematic search across scholarly
databases, standards/patents and current vendor documentation; publish inclusion/exclusion criteria
and comparison dimensions; obtain domain and cryptographic expert review; implement interoperable
test vectors; and empirically compare the protocol with relevant provenance approaches. Until then,
only Level 1 factual statements and the scoped Level 2 differentiation statement are permitted.

## Review outcome needed

Maintainers must either accept the architecture/profile and authorize a separate implementation,
request changes, or reject it. This ADR remains PROPOSED and makes no production change.
