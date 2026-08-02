# Passport trust-bundle API

`GET /api/v1/passport-trust-bundles/current` is authenticated, workspace authorized, flag gated,
and backed only by an injected server-controlled Phase 3A provider. It returns public lifecycle
bytes, optional anchor signature, version/checksum, and explicit trust mode. Retired and revoked
public records remain retained.

Before serving, the API requires canonical strict JSON, lifecycle schema and checksum validity,
metadata consistency, bounded bytes, and an issuer equal to the authenticated organization. A
substituted issuer or malformed provider result is treated as unavailable without disclosing why.

There is no arbitrary issuer, anonymous enumeration, remote discovery, credential, or private key.
Receiving passport and trust bundle together does not establish initial trust; anchors require an
independently authenticated channel.
Durable rollback state and initial anchor authentication remain provider/verifier responsibilities;
the endpoint does not claim to bootstrap either property.
