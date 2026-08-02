# Offline Answer Passport verification

An export contains `passport.json`, `passport.sig`, `export-manifest.json`, and possibly
`trust-bundle.json`. Verification requires no LLM, document retrieval, re-answering, private
document upload, or private key.

```text
ekip-vap verify passport.json passport.sig \
  --trust-bundle trust-bundle.json

python -m app.passport.cli verify \
  passport.json passport.sig \
  --trust-bundle trust-bundle.json
```

- Exit 0: `VERIFIED`.
- Exit 2: review-required states including `VERIFIED_WITHOUT_SNAPSHOT`, `STALE`, `EXPIRED`, and
  `INDETERMINATE`.
- Exit 1: invalid, revoked, modified, unknown-key, malformed, or trust-failure states.

Signature validity is not proof of universal truth or current factual validity. Stale, expired,
retired, and revoked conditions require the applicable policy review.

Obtaining the passport and trust bundle from the same service does not by itself establish initial
trust. Authenticate the trust anchor through an independently trusted channel.
