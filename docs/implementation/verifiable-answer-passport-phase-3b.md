# Verifiable Answer Passport Phase 3B

Phase 3B persists only an already-issued `vap-1` artifact after the existing static support gate and
offers authenticated, tenant/workspace-scoped metadata and export. Issuance, persistence, and export
remain independently disabled by default. Persistence failure never changes the supported answer,
retrieves again, regenerates, or signs twice.

The database preserves exact canonical manifest bytes and detached JWS. PostgreSQL rejects UPDATE
and DELETE through an explicit migration trigger, and a separate INSERT trigger rejects a workspace
whose authoritative organization differs from the row organization. The repository exposes persist and scoped read
only: no list, replace, update, delete, unscoped lookup, public issuance, or evidence snapshot.

Exports contain fixed `passport.json`, `passport.sig`, and `export-manifest.json` entries. An
injected approved provider may add public-only `trust-bundle.json`. Corrupt artifacts are denied.
Provider material is canonical-schema/checksum/issuer validated and size bounded before use; the
completed ZIP is also bounded before a response exists.
Editors may export retired, stale, or expired records with explicit status; revoked forensic export
requires admin. No state is labelled verified without current trust.

Phase 4 requires independent backend authorization review before frontend work. Production keys,
anchor ceremonies, publication, retention/redaction, and AWS/KMS/HSM remain future work.
