# Trust bootstrap

A trust-bundle signature proves only that the holder of the configured anchor private key signed
the supplied bytes. It does not establish why that anchor should be trusted. An offline verifier
must receive the anchor public record and expected issuer through an independently authenticated
channel and maintain the latest accepted bundle state outside this library.

The passport signing key does not automatically sign its own bundle. The optional injected anchor
is separate and ephemeral in tests. Unknown, modified, revoked, expired, or substituted anchors
fail closed. Unsigned artifacts are accepted only under an explicit local-test policy. A production
root, ceremony, distribution channel, compromise process, and durable rollback state are deferred.

The in-memory trusted state and registry provide process-local semantics only. Production must
distribute the initial anchor over an independently trusted channel and durably, atomically persist
accepted version/checksum state; an untrusted publication location cannot bootstrap its own trust.
