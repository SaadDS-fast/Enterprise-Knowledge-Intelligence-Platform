# Passport frontend threat model

Threats include IDOR, misleading validity claims, unknown-status downgrade, unsafe filename/CRLF
injection, content-type confusion, oversized download, archive execution, binary persistence,
object-URL leakage, trust-bootstrap confusion, and private-content telemetry.

Controls are authenticated existing transport, backend tenant/role enforcement, non-enumerating
errors, backend-computed statuses, fail-closed unknown mapping, UUID-derived filenames, exact media
type and byte limits, opaque Blob handling, immediate object-URL revocation, and no browser storage
or analytics. The trust warning explicitly denies same-service bootstrap.

Residual risks are production trust-anchor distribution, production signer/provider operations,
durable audit/outbox design, retention/redaction, and independent accessibility/security review.
No evidence, private key, production signer, AWS/KMS, update/delete/list API, or thesis mitigation
logic is introduced.
