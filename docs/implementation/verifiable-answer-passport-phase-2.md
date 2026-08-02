# Verifiable Answer Passport Phase 2

Status: internal supported-answer issuance integration

Phase 2 adds a disabled-by-default post-support hook to Standard Search. The hook runs only after
the canonical response state, final answer, verified claims, displayed citations, authorization
scope and generation result are final. It does not participate in retrieval, support scoring,
conflict handling, generation or refusal.

`ANSWER_PASSPORT_ENABLED` defaults to `false`. Disabled execution constructs no projection and
calls neither issuer nor signer. Enabled execution without an explicitly injected signer returns
the internal `SIGNER_UNAVAILABLE` state; the supported answer is unchanged and no unsigned or
temporary-key artifact is produced.

The frozen `SupportedAnswerProjection` contains exact answer bytes, normalized verified claims,
displayed claim/citation mappings, minimal displayed evidence-span bytes for hashing, opaque
document IDs, authoritative database version/checksum metadata, organization/workspace scope
inputs, named policy/configuration versions, provider/model metadata, completion time and safe
correlation ID. Prompts, reasoning, scores, undisplayed candidates, ACLs, tokens and secrets are
not representable because all projection models forbid extra fields.

The production adapter accepts the finalized server `SearchResponse`, not a request DTO. It reads
the canonical support decision and displayed mappings, resolves each displayed chunk through an
authorized workspace-scoped database join, and derives organization/workspace scope from the
server database. Client support flags, tenant IDs, citations, checksums, versions, verifier data
and signer key IDs are never accepted.

Eligible results are final `SUPPORTED` or `SUPPORTED_COMPOSITE` states with no unresolved conflict,
complete exact claim/citation coverage, authorized document mappings, valid versions/checksums,
complete scope and configuration, and (when generation was used) successful claim verification.
Refusals, conflicts, operational errors, cancellations, incomplete mappings and unsupported
Agent/Research terminal shapes are ineligible.

The request-scoped coordinator invokes the signer once. Concurrent duplicate hooks receive the
same cached result. Signer failure returns `FAILED` without an artifact or exception detail.
Cancellation records a request-local failed result and prevents silent reissuance. Durable
cross-request deduplication is deferred until a persistent passport lifecycle exists.

Internal statuses are `NOT_REQUESTED_OR_DISABLED`, `ISSUED`, `INELIGIBLE`, `SIGNER_UNAVAILABLE`
and `FAILED`. Issued data remains internal; Phase 2 adds no API field, route, event, download,
frontend workflow, database record or evidence exporter.

Minimal safe audit metadata can be emitted through an injected audit sink. Production audit-table
persistence is deferred until a secure signer and passport lifecycle are wired. Tests enforce that
audit metadata excludes answer text, claims, evidence, signatures and private-key material.

Agent and Research outputs remain unchanged and ineligible because their current final boundaries
do not provide the complete authoritative document-version/checksum and exact displayed mapping
contract. Extractive Search, verified Ollama Search and Ollama fallback Search share the common
Search finalization boundary and are eligible when their canonical state satisfies the guard.

Phase 3 prerequisites are a non-exportable production signer, tenant key policy, durable
idempotency/lifecycle design, authorized artifact storage, audit wiring, access control and threat
review. Public APIs, UI, downloads and evidence export require those prerequisites.
