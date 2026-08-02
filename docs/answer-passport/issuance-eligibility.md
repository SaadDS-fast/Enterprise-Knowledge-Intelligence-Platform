# Passport issuance eligibility

Issuance requires all of the following:

- server feature flag enabled and an explicitly injected signer available;
- canonical final state `SUPPORTED` or `SUPPORTED_COMPOSITE`;
- no refusal, conflict, operational failure or cancellation;
- final answer and support decision complete;
- unique verified claims with exact displayed citation coverage;
- every citation mapped to an authorized workspace document;
- authoritative document version and lowercase SHA-256 checksum present;
- organization/workspace scope, export policy and protocol/configuration versions present;
- server-derived provider metadata and approved model digest when generation was used; and
- verified generation/claim mapping when a generated answer was selected.

Neutral internal rejection reasons are `FEATURE_DISABLED`, `RESULT_NOT_SUPPORTED`,
`CONFLICT_NOT_ELIGIBLE`, `INCOMPLETE_CLAIM_MAPPING`, `INCOMPLETE_CITATION_MAPPING`,
`MISSING_SCOPE`, `SIGNER_UNAVAILABLE` and `ISSUANCE_ERROR`. They are not included in the normal
answer response.

Conflicts are never eligible, even with valid citations. A result already resolved by the existing
logic may be eligible only if its final canonical state is supported and non-conflicting. Future
conflict passport policy would require a separately designed schema and is not Phase 2 behavior.
