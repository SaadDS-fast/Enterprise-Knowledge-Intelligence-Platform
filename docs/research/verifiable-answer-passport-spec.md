# Verifiable Answer Passport and Offline Audit Replay

Status: **PROPOSED specification**

Version: draft 0.1, 2026-08-01

Implementation: none in this phase

## Product definition

A Verifiable Answer Passport (VAP) is a portable, signed manifest issued only after the existing
static support gate has accepted an answer. It binds answer bytes, normalized claims, exact
citation/evidence mappings, document versions/checksums, scope and named runtime configuration to
an issuance time. An independent CLI can validate it deterministically without retrieval, an LLM,
or a network call by default.

Suggested product name: **GroundSeal Passport**. “GroundSeal” is a working name and requires
trademark/domain review before external use.

## User problem and users

Auditors, compliance analysts, knowledge owners, incident reviewers and regulated application
teams can see citations in an answer but may be unable to prove later that the answer, citations
and referenced evidence identifiers are unchanged. Live-platform audit access is also a poor
portability boundary. VAP provides an independently checkable integrity record without claiming
universal truth.

## Preconditions and non-goals

Issuance requires `answer_state == supported` from the existing pipeline. Refused, conflicted,
partially supported, or unverified outputs are ineligible.

Non-goals:

- diagnosing evidence or retrieval quality;
- retrying, reformulating, retrieving, regenerating, or recovering evidence;
- changing support thresholds, retrieval configuration or generation behavior;
- proving factual truth beyond the supplied evidence;
- replacing authorization, document retention, legal hold, PKI, or timestamp-authority systems;
- embedding evidence by default; and
- using blockchain.

## Artifact set

1. `passport.json`: UTF-8 canonical manifest.
2. `passport.sig`: detached signature envelope.
3. Optional `evidence-snapshot/`: separately authorized content plus its canonical manifest.
4. Optional `trust-bundle.json`: public keys/certificates, policy and a signed revocation snapshot.

The base passport must remain useful without private evidence. The optional snapshot is never
implicit.

## Normative manifest shape

```json
{
  "schema_version": "vap-1",
  "certificate_id": "urn:uuid:...",
  "answer": {
    "media_type": "text/plain; charset=utf-8",
    "sha256": "base64url..."
  },
  "claims": [{
    "claim_id": "opaque-stable-id",
    "normalized_sha256": "base64url...",
    "citations": [{
      "evidence_id": "opaque-evidence-id",
      "evidence_span_sha256": "base64url...",
      "document_id": "opaque-document-id",
      "document_version": "opaque-version",
      "document_sha256": "base64url...",
      "applicability": {"policy_id": "declared-policy-id"}
    }]
  }],
  "scope": {
    "tenant_workspace_fingerprint": "base64url...",
    "audience": "opaque-audience-policy-id"
  },
  "assurance": {
    "support_gate_version": "...",
    "verifier_version": "...",
    "retrieval_configuration_sha256": "base64url...",
    "generation_provider_alias": "...",
    "approved_model_digest": "optional-base64url..."
  },
  "issued_at": "RFC3339 timestamp",
  "freshness": {
    "policy_id": "...",
    "not_after": "optional RFC3339 timestamp"
  },
  "signing": {"algorithm": "EdDSA", "key_id": "opaque-kid"}
}
```

Exact evidence byte-range/page anchors may be included if they are already authorized citation
metadata. Raw prompts, access tokens, roles, ACL membership, secrets, private keys and plaintext
evidence are forbidden in the base manifest. Free-form fields are prohibited in v1 to minimize
covert leakage and canonicalization ambiguity.

## Canonicalization and cryptography

- Serialize `passport.json` using JSON Canonicalization Scheme (JCS), [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785).
- Hash content with SHA-256; domain-separate each digest input, for example
  `VAP1\0ANSWER\0<bytes>`, to prevent cross-field substitution.
- Sign the canonical manifest with Ed25519/EdDSA as specified by
  [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032).
- Encode the detached signature as JWS with an allowlisted `alg`, protected `kid`, explicit
  `typ`, and no unprotected security parameters, following
  [RFC 7515](https://www.rfc-editor.org/rfc/rfc7515). A future COSE profile may be added only as a
  separately versioned interoperability choice.
- Reject duplicate JSON keys, non-I-JSON values, unknown critical fields, algorithm substitution,
  invalid encodings and noncanonical manifests.

JCS + SHA-256 + Ed25519 + detached JWS is preferred over a custom signature format. Cryptography
detects modification; it does not establish truth, authorization, or current applicability.

## Issuance flow

1. Receive an immutable projection of an already-supported answer; reject all other states.
2. Revalidate projection completeness and tenant/workspace consistency without searching.
3. Normalize claim representations using a versioned, deterministic function already represented
   by the supported answer. Do not ask a model to create new claims.
4. Hash answer, claims, evidence spans and documents with field-domain separation.
5. Build and JCS-canonicalize the manifest.
6. Ask the configured signer to sign the canonical bytes.
7. Persist an issuance audit event containing certificate ID, manifest digest, key ID and actor;
   never persist private key material.
8. Export the base artifact and, only with separate authorization, a snapshot.

Idempotency: the same immutable projection, explicit issue timestamp, policy and key produce the
same canonical manifest/signature. Certificate IDs must be unique; a duplicate ID with different
manifest bytes is a hard failure.

## Deterministic offline verification

Default CLI contract:

```text
groundseal verify passport.json passport.sig \
  --trust-bundle trust-bundle.json \
  [--answer answer.txt] \
  [--snapshot evidence-snapshot/] \
  [--at 2026-08-01T12:00:00Z] \
  --format json
```

The verifier performs, in order:

1. bounded-size parsing, schema validation and canonicalization;
2. protected-header/algorithm/key-policy validation;
3. detached signature verification;
4. optional supplied-answer hash validation;
5. claim/citation/manifest consistency validation;
6. optional snapshot manifest, evidence span, document hash and scope validation;
7. configuration/verifier fingerprint comparison if an expected policy supplies values;
8. expiry/freshness evaluation against an explicit verifier clock; and
9. revocation evaluation using the supplied signed trust bundle.

Stable result dimensions are independent:

```json
{
  "schema_valid": true,
  "signature_valid": true,
  "key_status": "trusted",
  "content_integrity": "valid|invalid|not_supplied",
  "snapshot_integrity": "valid|invalid|not_supplied",
  "scope_match": "valid|invalid|not_evaluated",
  "configuration_match": "valid|invalid|not_evaluated",
  "freshness": "fresh|expired|version_mismatch|unknown",
  "overall": "valid|invalid|valid_review_required"
}
```

`overall=valid` never means universally true. Unknown freshness must not invalidate a sound
historical signature; it yields `valid_review_required` under the default policy. No status can
trigger retrieval or generation.

## Key management and revocation

- Development may use file-backed test keys; production should use a KMS/HSM or OS-backed signer
  with non-exportable private keys.
- Separate signing keys by environment and tenant policy; use least-privilege signing identities.
- Rotate keys on a published schedule. Preserve retired public keys for historical verification.
- A `kid` is an identifier, never a key or secret.
- Trust bundles are explicit, versioned and signed. They can mark a key `trusted`, `retired`, or
  `revoked` with effective time and reason code.
- Offline revocation is only as current as the supplied trust bundle. The verifier must report the
  bundle timestamp and must not silently make a network call. Optional online refresh requires an
  explicit flag and is outside the default verification result.
- Compromise response invalidates affected signatures according to policy/effective time; it does
  not rewrite historical artifacts.

## Replay, freshness, portability and privacy

Replay of a valid old passport is addressed through unique IDs, `issued_at`, optional `not_after`,
audience/scope fingerprints, and verifier policy. A copied passport remains cryptographically
valid but can be expired, revoked, outside audience or stale. These facts must be shown separately.

Document freshness is evaluated only against versions/checksums supplied in an authorized snapshot
or explicit local policy data. Without those inputs it is `unknown`, never guessed. No retrieval is
performed to locate a current document.

Portability depends on a frozen schema/profile, canonical test vectors, stable hash normalization,
public-key distribution and machine-readable result codes. References to proprietary model or
configuration identities are opaque strings/hashes so the verifier need not run that provider.

Hashes can confirm guesses about low-entropy evidence and identifiers can disclose organizational
structure. Use opaque tenant-scoped identifiers, domain-separated hashes (optionally policy-keyed
for sensitive low-entropy spans), minimal metadata, export authorization, encrypted snapshots,
audience binding, retention limits and audit logging. Signature validity never confers evidence
access.

## API and UI feasibility plan

Proposed later implementation; names are illustrative and do not alter current contracts:

- Backend modules: `passport/schema`, `canonicalize`, `hashing`, `issuer`, `signer`, `trust`,
  `verifier`, `snapshot_export`, and audit adapter.
- Database: passport issuance record (ID, answer/run reference, manifest digest, key ID, timestamps,
  status) and key/trust metadata. Store artifacts in scoped object storage; avoid duplicating
  evidence. A migration is required.
- New endpoints: issue, metadata/status, authorized artifact download, authorized snapshot export,
  and optional server-side verify. Existing query APIs stay unchanged.
- Frontend: supported-answer “Issue passport” action, passport detail/status view, export dialog,
  and offline-verification instructions. No action appears on refusals.
- CLI: standalone, dependency-minimal verifier with JSON and human output, fully usable air-gapped.
- Documentation: schema/profile, threat model, key ceremony/rotation, recovery, operator and auditor
  guides, test vectors and privacy guidance.

## Phased implementation estimate

| Phase | Scope | Solo estimate |
|---|---|---|
| 0 | Threat model, schema profile, golden vectors, key policy | 3–5 days |
| 1 | Pure canonicalizer/hash/signature library and offline CLI | 1–2 weeks |
| 2 | Issuance adapter, scoped persistence, audit and migrations | 1–2 weeks |
| 3 | Export/status APIs and minimal UI | 1–2 weeks |
| 4 | Authorized snapshot verification, revocation bundle, hardening | 2 weeks |
| 5 | Browser/security/interoperability tests and documentation | 1 week |

Practical total: approximately **6–9 focused developer-weeks**, excluding external security review,
procurement and production KMS integration lead time.

## Test strategy and acceptance criteria

Unit fixtures must cover JCS bytes, domain-separated digests, Ed25519/JWS vectors, schema limits,
duplicate keys, Unicode/number edge cases, unknown algorithms, clock boundaries and stable result
codes. Integration tests cover supported-only issuance, authorization, scoped storage, audit,
rotation/revocation, migration rollback and cross-tenant denial. Browser tests cover issue/status/
export and absence on refusal. Security tests cover confused-deputy signing, key-ID substitution,
zip/path bombs, oversized manifests, snapshot traversal, metadata leakage, replay, tampering and
cross-tenant snapshots.

Acceptance requires:

1. issuance is impossible for every non-supported answer state;
2. the CLI works with network disabled, no LLM and no retrieval dependency;
3. golden artifacts verify identically across two independent process invocations;
4. one-byte mutations to answer, claim, citation, evidence span, manifest and signature are detected;
5. signature validity is reported separately from freshness, revocation and authorization;
6. a snapshot is never exported without explicit scoped authorization and contains no secrets;
7. version/config/verifier mismatch results are deterministic and never invoke search;
8. key rotation preserves verification under the declared historical policy;
9. cross-tenant requests fail closed without leaking identifiers or evidence; and
10. existing support, refusal, isolation and grounding behavior is unchanged.

## Novelty-claim ladder

- **Level 1 — factual:** “GroundSeal issues a signed manifest for an already-supported answer and
  verifies it offline against optional authorized evidence snapshots.” Use only after acceptance
  tests pass.
- **Level 2 — differentiated:** “It combines verified grounding with portable, independently
  verifiable answer evidence—a combination not commonly documented in the official
  enterprise-assistant products reviewed as of 2026-08-01.” Always attach review scope/date.
- **Level 3 — research novelty:** “The passport protocol is a novel answer-provenance method.” Do
  not use without a systematic literature review, protocol comparison, expert review and empirical
  evidence beyond this bounded scan.

Rejected wording: “world first,” “never done before,” “unique in the entire market,” “guarantees
universal truth,” and “impossible to tamper with.”

## Major risks

Canonicalization divergence, signer compromise, stale trust bundles, over-disclosure, hash guessing,
misleading “verified” UI language, loss of historical public keys, snapshot retention, and scope
creep into re-answering are the principal risks. The mitigations above reduce but do not eliminate
them; an independent cryptographic/security review is required before production use.
