# Trust bootstrap

A trust-bundle signature proves only that the holder of the configured anchor private key signed
the supplied bytes. It does not establish why that anchor should be trusted. An offline verifier
must receive the anchor public record and expected issuer through an independently authenticated
channel and maintain the latest accepted bundle state outside this library.

The passport signing key does not automatically sign its own bundle. The optional injected anchor
is separate and ephemeral in tests. Unknown, modified, revoked, expired, or substituted anchors
fail closed. Unsigned artifacts are accepted only under an explicit local-test policy. A production
root, ceremony, distribution channel, compromise process, and durable rollback state are deferred.
