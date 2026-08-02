# Verifiable Answer Passport Phase 4

Phase 4 adds a post-answer frontend assurance workflow. A supported Search response receives an
optional `passport_reference` only after server-side issuance and durable persistence succeed. The
reference contains the protocol ID, `vap-1`, and server-computed metadata/export availability; it
never contains a manifest, signature, evidence, answer copy, tenant name, or signer internals.

The Search answer remains unchanged. A reference renders a small Answer Passport control that
loads authorized metadata only after user action. Refusal, conflict, error, unpersisted, Agent, and
Research outputs have no reference and therefore trigger no passport lookup or implied failure.

All issuance, integrity, lifecycle, scope, and export decisions remain backend-authoritative.
Defaults remain disabled. There is no client issuance, signing, evidence export, production signer,
cloud integration, or retrieval/generation change. Phase 5 requires production provider design,
durable trust publication, independent authorization review, and trust-anchor operations.
