# Passport trust-bundle API

`GET /api/v1/passport-trust-bundles/current` is authenticated, workspace authorized, flag gated,
and backed only by an injected server-controlled Phase 3A provider. It returns public lifecycle
bytes, optional anchor signature, version/checksum, and explicit trust mode. Retired and revoked
public records remain retained.

There is no arbitrary issuer, anonymous enumeration, remote discovery, credential, or private key.
Receiving passport and trust bundle together does not establish initial trust; anchors require an
independently authenticated channel.
