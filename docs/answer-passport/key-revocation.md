# Answer Passport key revocation

Revocation is explicit and irreversible from pending, active, or retired state. It records UTC
time and one public code: `KEY_COMPROMISE`, `SUPERSEDED`, `CESSATION_OF_OPERATION`,
`POLICY_VIOLATION`, or `UNSPECIFIED`. Confidential investigation text is prohibited.

Revocation must not predate creation, activation, or retirement. Once present, it has final-policy
precedence over retirement, current key expiry, passport or bundle freshness, historical validity,
and a cryptographically successful signature. The verifier reports revocation rather than
weakening it to a freshness warning.

The key remains in lifecycle trust metadata. Revocation is not deletion, retirement, expiry, or
signature corruption. Passport verification must continue to separate cryptographic validity,
issuance-time key validity, current lifecycle/revocation state, freshness, and final policy. Phase
3A does not locate, retrieve, regenerate, or re-answer affected passports.
