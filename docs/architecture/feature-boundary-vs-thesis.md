# Feature boundary versus thesis-reserved work

Status: proposed architecture constraint, 2026-08-01.

## Purpose

The Verifiable Answer Passport is a post-answer integrity feature. It is not a retrieval-quality,
knowledge-coverage, or recovery feature. The unpublished thesis remains isolated by keeping a
one-way boundary after the existing support decision.

```text
existing query pipeline (unchanged)
  ├─ insufficient support ──> neutral refusal ──> STOP
  └─ supported answer
       └─ immutable issuance projection
            └─ canonical manifest ──> signature ──> passport/export
                                      |
supplied passport + optional authorized snapshot
  └─ offline verifier (schema/hash/signature/version checks only)
```

## Allowed inputs and outputs

Issuance may consume only data already produced for a supported answer: answer text, normalized
claims, exact authorized citation mappings, evidence/document/version identifiers and checksums,
scope fingerprint, timestamps, and named configuration/verifier/provider identities. It emits a
canonical manifest and detached signature.

Verification consumes a passport, public verification material, an explicit trust policy and,
optionally, an authorized evidence snapshot. It emits deterministic integrity and freshness fields.
It does not assert that the answer is universally true.

## Dependency rule

Allowed dependency direction:

`supported answer DTO → passport issuer → canonicalization/signing`

`passport/snapshot/public keys → offline verifier → verification report`

Forbidden dependencies from issuer or verifier: retriever, query planner, embedding provider,
reranker, search connector, generation provider, agent tool execution, or any network client in the
default verification path. Provider/model identifiers are opaque manifest values, not callable
configuration.

## Thesis-reserved and prohibited behavior

- classifying or attributing why evidence was inadequate;
- distinguishing retrieval failure from unavailable knowledge;
- retries or reformulation after weak support;
- changing candidate count, retriever, search extent or budget in response to support;
- locating replacement evidence or regenerating an answer during replay;
- user-facing technical reasons for insufficient support.

Any one of these is a boundary violation. The only low-support output remains neutral refusal.

## Safe lifecycle semantics

- `signature_valid` means bytes match a signature under an accepted key.
- `content_integrity_valid` means declared hashes match supplied content.
- `snapshot_evidence_valid` means supplied authorized evidence matches manifest hashes.
- `freshness_status` means timestamps/version assertions satisfy the verifier’s explicit policy.
- None of these fields means “factually true,” “currently applicable everywhere,” or “authorized
  for every viewer.”
- Expiry or a version mismatch yields review-required status; it never starts a query.

## Privacy and authorization boundary

The base passport contains identifiers, hashes and fingerprints—not evidence text, access tokens,
ACLs, prompts, secrets, or signing private keys. Identifiers can still be sensitive and must use
tenant-scoped opaque values. Evidence snapshots are separate, explicit, least-privilege exports;
they are encrypted at rest/in transit, audience-scoped and omitted by default. A valid signature
does not grant access.

## Architectural acceptance tests

- A refused response cannot enter issuance.
- Verifier tests pass with network access disabled and no model installed.
- Static dependency checks prove no issuer/verifier imports from retrieval/generation.
- Mutation fixtures independently detect answer, claim, citation, evidence and signature changes.
- Cross-tenant snapshots fail scope matching without revealing content.
- Expiry and version mismatches never invoke search and return stable status codes.
- Existing support/refusal test suites remain unchanged and passing when implementation begins.
