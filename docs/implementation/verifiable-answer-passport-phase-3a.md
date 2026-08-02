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

Phase 1 `vap-trust-1` remains backward compatible. The lifecycle builder also emits a deterministic
public `vap-trust-1` projection for the existing offline verifier: pending records are omitted;
active, retired, and revoked records retain status and lifecycle cutoffs. This is an in-process
compatibility artifact, not a publication endpoint.

Registry publication is the linearization point for activation, rotation, retirement, and
revocation. Signing linearizes when provider signing completes while the issuer registry lock
excludes a terminal transition. A sign that wins the lock completes with its originally resolved
active key; a transition that wins first makes signing fail closed. Rotation publishes successor
activation and predecessor retirement in one mutation. Bundle generation takes one versioned
registry snapshot.

Revocation is irreversible and dominates retirement, key/passport/bundle freshness, and historical
validity in final policy. Retirement and key expiry are not signature corruption: issuance is
evaluated separately against validity and retirement cutoffs. Bundle processing orders
schema/canonical/checksum and lifecycle failures before rollback/chain/history, anchor/signature,
then freshness. Exact version/checksum replay is idempotent; other same-version content and invalid
higher-version chains fail.

Phase 3B prerequisites include reviewed durable atomic storage, non-exportable deployment-specific
signers, tenant/environment policy, bundle-version allocation, authenticated publication,
production audit persistence, access control, retention, incident policy, and external security
review. None is implied by this foundation.
