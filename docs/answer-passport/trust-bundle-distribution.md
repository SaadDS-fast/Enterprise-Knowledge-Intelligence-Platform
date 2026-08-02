# Trust-bundle distribution foundation

The `vap-trust-1` / `vap-key-lifecycle-1` artifact contains issuer, monotonic bundle version,
generation/refresh/expiry times, EdDSA allowlist, deterministically ordered public key records,
metadata checksums, bundle checksum, optional previous checksum, and optional distinct anchor ID.
Pending, retired, and revoked records are retained. It contains no private material or credentials.

Offline validation checks strict canonical schema, checksum, issuer, algorithms, key uniqueness and
encoding, lifecycle timestamps and links, rollback/version collision, previous-checksum chain,
historical-key removal, optional signature, and freshness. Integrity failures are separate from
`STALE` and `EXPIRED`. No HTTP endpoint, network refresh, persistent accepted state, or production
publication exists in Phase 3A.

Precedence is schema/canonical/checksum, lifecycle validity, trusted-state rollback/chain/history,
anchor/signature, then freshness. Exact same-version/same-checksum replay is idempotent;
same-version/different-checksum is a collision, and a higher version must name the latest checksum.
Retired and revoked records may not disappear. Versions are bound to registry revisions, so
unchanged state cannot masquerade as an advance. The deterministic Phase 1 verifier projection
carries no private material.
