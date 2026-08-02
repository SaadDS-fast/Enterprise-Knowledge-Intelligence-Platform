# Passport persistence and export architecture

The coordinator accepts only `ISSUED`, parses canonical VAP-1/JWS bytes, recomputes scope, and uses a
tenant-aware repository savepoint. A domain-separated SHA-256 idempotency key binds scope, safe
correlation ID, signed answer hash, schema, and policy. Exact retries return one record; conflicting
reuse fails closed.

Every read includes passport, organization, and workspace IDs derived from authenticated tenant
context. Metadata is viewer-readable; export requires editor; revoked forensic export requires
admin. Missing and cross-tenant artifacts share the same 404 behavior.

Checksums, canonical schema, signed ID/scope/key/answer/time bindings, and optional injected public
trust are checked before output. The trust provider is server-controlled with no network discovery.
