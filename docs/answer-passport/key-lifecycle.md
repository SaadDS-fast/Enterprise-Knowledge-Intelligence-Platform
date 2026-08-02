# Answer Passport key lifecycle

`PENDING` is public metadata prepared for explicit future activation and cannot sign. `ACTIVE` is
the sole issuance key for an issuer and may sign only within its validity interval with a matching
provider key. `RETIRED` cannot issue new signatures but remains public for historical verification.
`REVOKED` cannot sign, remains public, carries an effective time and bounded reason, and is
irreversible.

Allowed transitions are `PENDING→ACTIVE`, `PENDING→REVOKED`, `ACTIVE→RETIRED`,
`ACTIVE→REVOKED`, and `RETIRED→REVOKED`. Every reverse transition, transition to pending,
same-state transition, activation bypassing correspondence checks, revocation without a reason,
and key-ID reuse is rejected. Activation is explicit; no scheduler or background service exists.

Activation, retirement, and revocation linearize when the registry publishes the validated
immutable snapshot. Rotation publishes both changes together. Cancellation before assignment can
leave only a harmless pending successor; after assignment the operation is committed. Audit-sink
cancellation or failure after commit does not alter lifecycle state.

Metadata is immutable, extra-forbidden, UTC-only, EdDSA-only, canonically Base64URL encoded, and
SHA-256 checksummed. It contains issuer/key identifiers, raw public Ed25519 bytes, lifecycle and
validity timestamps, generation and predecessor/successor links, and bounded public revocation
metadata—never tenant names, ACLs, credentials, private bytes, or incident details.
