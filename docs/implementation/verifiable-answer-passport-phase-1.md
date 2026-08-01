# Verifiable Answer Passport Phase 1

Status: implemented cryptographic core and offline verifier

## Scope

Phase 1 provides a pure `backend/app/passport` package with:

- the narrow `vap-1` manifest schema;
- RFC 8785-compatible canonical JSON for the schema's integer-only number profile;
- domain-separated SHA-256 content bindings;
- Ed25519 detached JWS signing and verification;
- an explicit local `vap-trust-1` trust bundle;
- an optional, synthetic-only `vap-snapshot-1` evidence snapshot validator;
- a synthetic fixture builder that makes supported-only eligibility executable without production
  answer integration;
- independent signature, answer-integrity, scope, configuration and freshness results; and
- the `ekip-vap` / `python -m app.passport.cli` offline verifier.

It does not issue passports from application answers. It adds no API, database, frontend,
retrieval, generation, benchmark, deployment or AWS behavior. Snapshot **verification** is present;
production evidence export, authorization and encryption workflows remain deferred.

The canonicalizer is custom code and is accurately classified as a **restricted RFC
8785-compatible profile** for the tested JSON domain. It implements compact UTF-8 serialization,
UTF-16 property ordering and strict parsing, but intentionally rejects all fractional/exponent
numbers and non-finite values. Integers are limited to the I-JSON safe range. Strings are not
Unicode-normalized, matching JCS semantics; invalid surrogate sequences, duplicate keys, inputs
deeper than 64 containers and noncanonical encodings are rejected. This is not a claim of complete
RFC 8785 conformance for every JSON number.

Ed25519 is provided by PyCA `cryptography`; detached compact-JWS construction and validation are a
narrow custom implementation. Only a protected `alg=EdDSA`, `kid`, and
`typ=application/vap+jws` header is accepted. Untrusted input cannot select another algorithm.
`cryptography>=46,<51` is now a direct Apache-2.0-or-BSD-3-Clause dependency because the passport
imports it directly. Pydantic remains the existing direct MIT-licensed schema dependency
(`>=2.11,<3`). PyJWT remains an existing MIT-licensed dependency (`[crypto]>=2.10,<3`) for the wider
application, but the passport JWS code does not call PyJWT. CFFI is cryptography's transitive
foreign-function-interface dependency. Validation used cryptography 49.0.0, Pydantic 2.13.4 and
PyJWT 2.13.0 locally; the clean Docker resolver selected cryptography 50.0.0 within the declared
range.

## Verify an artifact

From an installed backend environment:

```bash
ekip-vap verify passport.json passport.sig \
  --trust-bundle trust-bundle.json \
  --answer answer.txt \
  --snapshot evidence-snapshot.json \
  --at 2026-08-01T00:00:00+00:00 \
  --format json
```

Equivalent source-tree invocation:

```bash
python -m app.passport.cli verify passport.json passport.sig \
  --trust-bundle trust-bundle.json --format json
```

The command performs no network operation. Exit code `0` means cryptographically valid
(`valid` or `valid_review_required`); exit code `1` means invalid or an input/file error. There is no
debug mode and normal invalidity produces no stack trace. The stable machine result schema reports:

- `VERIFIED`: signature and supplied snapshot validated;
- `VERIFIED_WITHOUT_SNAPSHOT`: signature valid; evidence content was not independently checked;
- `EXPIRED`: valid historical signature with expired passport/key freshness;
- `STALE`: snapshot document version differs;
- `REVOKED`, `INVALID_SIGNATURE`, `CONTENT_MODIFIED`, `SNAPSHOT_MISMATCH`, `UNKNOWN_KEY`,
  `INVALID_SCHEMA`, `UNSUPPORTED_ALGORITHM`, or `INDETERMINATE`.

Precedence is schema/canonical form → protected envelope → key lookup → signature → revocation →
historical key interval → answer/scope/configuration → verification time → snapshot → freshness.
The first failing gate determines `status` and `errors`; independent fields preserve checks already
completed. Missing snapshots remain `not_supplied`, never `valid`.

Machine output keeps signature validity separate from supplied-answer integrity, snapshot
integrity, historical/current key state and freshness. `valid` never means current factual truth,
universal correctness or authorization for every viewer.

## Trust and revocation limits

The verifier trusts only the bundle explicitly supplied by the caller. Key `not_before`/`not_after`
intervals establish historical issuance validity separately from current `trusted`, `retired`,
`revoked`, `expired`, or `not_yet_valid` state. A revoked key invalidates the artifact. A retired
key or expired/unknown freshness produces `valid_review_required` while preserving the historical
signature result. Because Phase 1 is offline, revocation knowledge is only as current as
`trust_bundle_generated_at`; no hidden refresh occurs.

The caller-provided trust bundle is the explicit local trust anchor; root signing/distribution of
that bundle, KMS/HSM integration, production key rotation and passport issuance remain future work.
Replacing the bundle with a different public key does not validate an existing signature. Test
private keys are ephemeral process-local fixtures that are never serialized. The
provisional product name **GroundSeal Passport** has not been trademark-cleared.

## Thesis boundary

The package imports no retrieval, reranking, generation, Agent, API, persistence or network module.
It receives complete artifact bytes and validates them. It cannot diagnose insufficient support,
retry, reformulate, change retrieval settings, recover evidence or explain a refusal.

## Validation

Focused tests cover canonicalization, strict parsing, domain separation, signature and key-ID
binding, all manifest security fields, snapshots, noncanonical JSON, lifecycle states,
scope/configuration mismatch, blocked sockets, synthetic issuance rejection and CLI behavior. All
issuance inputs are synthetic. The existing backend suite is also run to catch regressions without
executing consumed evaluation benchmarks.
