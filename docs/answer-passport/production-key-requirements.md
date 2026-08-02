# Production passport key requirements

Phase 2 intentionally provides no production signer. Default and production runtime therefore have
no signing key and fail closed for optional passport issuance.

A future signer must provide a stable opaque key ID and asynchronous signing operation while
keeping Ed25519 private material non-exportable. It must use environment/tenant separation,
least-privilege identities, explicit rotation/revocation policy, auditable access and a published
trust-bundle lifecycle. KMS/HSM or an equivalently reviewed OS-backed facility is required before
public issuance.

Forbidden key sources include committed keys, generic plaintext environment variables, automatic
production key generation, database private-key storage, key logging and test-key reuse. Phase 2
adds no PEM, seed, key path, cloud credential, AWS KMS or secret-manager configuration.

Tests use process-local ephemeral Ed25519 keys injected directly into the coordinator. They are
never serialized or written to disk. A production provider must preserve the same exact VAP-1 JWS
profile, at-most-once request semantics, cancellation behavior and sanitized failures.
