# Verifiable Answer Passport Phase 3A

Status: provider-neutral secure key-lifecycle and trust-distribution foundation.

Phase 3A adds strict immutable `PENDING`, `ACTIVE`, `RETIRED`, and `REVOKED` public
metadata, an atomic registry contract, an opaque private signer boundary, server-side active-key
resolution, deterministic lifecycle trust bundles, optional distinct trust-anchor signatures, and
offline rollback-aware validation. It is downstream of an already-supported answer.

The reference registry, passport signer, and trust-anchor signer are ephemeral in-memory test
implementations. There is no production key provider, private-key persistence/configuration,
automatic key creation, API, migration, frontend workflow, AWS/KMS/HSM integration, publication
endpoint, scheduler, passport storage, or evidence export. `ANSWER_PASSPORT_ENABLED` remains false
by default and no signer is wired in production.

Phase 1 `vap-trust-1` verifier input remains unchanged. Phase 3A's canonical bundle is explicitly
profiled as `vap-key-lifecycle-1`; a later compatibility/publication phase must define how a trusted
lifecycle snapshot is projected into distribution inputs without weakening Phase 1 precedence.

Phase 3B prerequisites include reviewed durable atomic storage, non-exportable deployment-specific
signers, tenant/environment policy, bundle-version allocation, authenticated publication,
production audit persistence, access control, retention, incident policy, and external security
review. None is implied by this foundation.
