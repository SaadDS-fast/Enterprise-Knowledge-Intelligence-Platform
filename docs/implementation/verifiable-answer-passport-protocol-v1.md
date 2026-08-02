# Verifiable Answer Passport protocol profile VAP-1

Status: Phase 1 implementation profile, 2026-08-01

## Versioned artifacts

| Artifact | Version | Purpose |
|---|---|---|
| Passport manifest | `vap-1` | Signed answer, claim, citation, document, scope and assurance bindings |
| Detached envelope | `application/vap+jws` | Standard encoded detached compact JWS with protected `alg`, `kid`, and `typ` |
| Trust bundle | `vap-trust-1` | Explicit offline public-key trust input and lifecycle metadata |
| Evidence snapshot | `vap-snapshot-1` | Optional synthetic authorized document/evidence bytes for offline checking |
| Hash profile | `VAP1` | Domain prefix used before every protected byte string |

All schemas reject unknown fields and bound collection sizes. Passport claims and citation IDs,
trust-bundle key IDs, and snapshot document/evidence IDs must be unique in their defined scopes.

## Canonicalization

The custom canonicalizer is a **restricted RFC 8785-compatible profile for the tested supported
JSON domain**, not a general claim of complete RFC 8785 conformance. It provides compact UTF-8 JSON,
UTF-16 code-unit property ordering, strict duplicate-key parsing, and I-JSON-safe integers. It
rejects fractional/exponent forms, NaN, infinities, invalid surrogates, unsupported types, integers
outside ±9,007,199,254,740,991, and nesting deeper than 64 containers. Unicode normalization is not
performed; canonically equivalent Unicode strings remain different protected byte strings.

## Content bindings

Every digest is:

```text
base64url_no_padding(SHA-256(version || NUL || domain || NUL || content))
```

Stable domains are `PASSPORT`, `ANSWER`, `CLAIM`, `EVIDENCE_SPAN`, `DOCUMENT`, `SCOPE`, and
`CONFIG`. The separators prevent boundary ambiguity; changing the version or domain changes the
digest. `PASSPORT` is available for artifact indexing and external manifests. The signature binds
the complete canonical passport directly.

## Signature envelope

PyCA `cryptography` supplies Ed25519 primitives; it is not a JOSE implementation.
`app.passport.jws` is a narrow custom implementation of **standard encoded detached JWS**: the
payload segment is omitted from compact serialization, while `BASE64URL(payload)` remains in the
JWS signing input. This follows the detached-content method in RFC 7515 Appendix F. It does **not**
use RFC 7797: `b64=false` and `crit=["b64"]` are absent and rejected.

The only accepted protected header is exactly:

```json
{"alg":"EdDSA","kid":"<opaque key id>","typ":"application/vap+jws"}
```

The compact form is `BASE64URL(protected)..BASE64URL(signature)` and the signing input is
`BASE64URL(protected) || "." || BASE64URL(payload)`. Protected-header JSON must use the VAP
canonical serializer. Base64URL is unpadded and canonical. The profile has no unprotected header.
`cty`, `crit`, `b64`, extensions, duplicate fields, unknown critical fields, altered type/key/
algorithm, noncanonical protected JSON, padding and non-minimal Base64URL are rejected. Because RFC
7797 is unsupported, a missing `crit` member is correct for this profile; adding `crit` is invalid.
The manifest key ID must equal the protected key ID.

The custom code remains justified only while this profile stays this narrow. Existing PyJWT public
APIs target JWT/general JWS workflows and do not provide the required strict VAP protected-header,
canonical-header and stable error/status contract without additional policy code. Unsupported JOSE
features include general JSON serialization, multiple signatures, unprotected headers, arbitrary
algorithms, RFC 7797, remote key discovery, embedded JWKs/X.509 chains and critical extensions.
Replacement with a maintained JOSE library is required if the profile expands, interoperability
partners require broader JOSE support, a suitable library can enforce the exact profile, or custom
envelope maintenance can no longer receive dedicated security tests/review.

Interoperability is proven in both directions by an independent test path using only Python's JSON/
Base64 libraries plus PyCA Ed25519: the production signer verifies under independently assembled
RFC 7515 signing input, and an independently assembled/signed envelope verifies in the production
verifier. The independent path does not call the production envelope builder or Base64 helpers.

## Trust and lifecycle

Each `vap-trust-1` key supplies a 32-byte raw Ed25519 public key, declared status, and timezone-aware
`not_before`/`not_after`. Revoked keys require `revoked_at`. Historical validity checks the passport
`issued_at` against the key interval. Current status is evaluated separately at the explicit
verification time. The bundle is an explicit local trust anchor; Phase 1 does not fetch keys or
revocation data and does not define root distribution/signing.

## Snapshot rules

The optional snapshot must match the passport certificate and scope fingerprints. Its document set
and evidence set must exactly equal the signed references: duplicates, omissions and unreferenced
extras fail. Supplied bytes are Base64URL-decoded and checked against the signed document and span
digests. Document-ID/version associations must match. A missing snapshot is
`VERIFIED_WITHOUT_SNAPSHOT`, never evidence-content verification.

This format is synthetic-only in Phase 1. There is no production evidence exporter, authorization,
encryption, retention or API workflow.

## Status precedence

Validation stops at the first failing gate:

1. input size, schema and canonical form;
2. protected envelope and algorithm;
3. key lookup and key-ID binding;
4. signature and revocation;
5. historical key interval;
6. supplied answer, expected scope and configuration;
7. verification clock/current key state;
8. optional snapshot;
9. passport/key freshness.

Stable statuses are `VERIFIED`, `VERIFIED_WITHOUT_SNAPSHOT`, `EXPIRED`, `STALE`, `REVOKED`,
`INVALID_SIGNATURE`, `CONTENT_MODIFIED`, `SNAPSHOT_MISMATCH`, `UNKNOWN_KEY`, `INVALID_SCHEMA`,
`UNSUPPORTED_ALGORITHM`, and `INDETERMINATE`. Detailed independent fields prevent freshness from
being represented as signature validity.

CLI automation maps status, not the broader `overall` field:

- exit `0` / `verified`: `VERIFIED` only;
- exit `2` / `review_required`: `VERIFIED_WITHOUT_SNAPSHOT`, `STALE`, `EXPIRED`, or
  `INDETERMINATE`;
- exit `1` / `invalid`: every trust, integrity, schema, algorithm, content, snapshot, unknown-key,
  malformed-input or file error, including `REVOKED`.

Expiry uses exit `2` because a valid historical signature remains distinguishable while policy
review is mandatory. Revocation uses exit `1` because the trust decision is invalid. JSON output
contains `status`, `exit_code`, and `exit_classification`; text output prints the same fields.

## Security boundary

Verification has no retrieval, generation, embedding, reranking, Agent, Research, API, persistence,
database, HTTP or socket dependency. It performs no network operation. Synthetic issuance accepts
only complete `supported` fixtures whose support flag is true and whose citations share the signed
scope. It cannot diagnose, retry, reformulate, recover evidence or explain a refusal.
