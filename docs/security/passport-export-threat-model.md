# Passport export threat model

Threats include IDOR, role/scope spoofing, idempotency collision, artifact substitution, checksum
tampering, stale/forked trust, archive/header injection, oversized input, audit injection, and
private/evidence leakage.

Controls include server-derived tenant context, scoped queries, generic 404s, role thresholds,
canonical/JWS validation, layered checksums, PostgreSQL scope and mutation triggers, collision-safe insert,
fixed uncompressed ZIP entries, safe UUID filename, no-store headers, and injected public-only
trust. Corruption fails closed without partial export or repair.

Trust material and final archives have hard byte ceilings. Lifecycle material is checked for
canonical schema, checksum, metadata consistency, and authenticated-tenant issuer binding before
it can enter a response.

Residual risks are initial anchor distribution, production audit durability, retention/redaction,
and multi-region transactions. No production signer, cloud keys, frontend, or evidence exporter is
included.
