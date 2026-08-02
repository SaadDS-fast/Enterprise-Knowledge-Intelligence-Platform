# Passport key-lifecycle architecture

The public metadata registry and private signing provider are separate interfaces. Registry atomic
mutation owns uniqueness, historical retention, relationship integrity, and the zero-or-one-active
invariant. The provider exposes only public-key lookup and signing by opaque key ID; it exposes no
raw private key, seed, serialization, credential, or filesystem operation.

Phase 2 may use `LifecyclePassportSigner`. It resolves the active key against the server issuance
time, writes that key ID into the manifest, then re-resolves before signing. A concurrent rotation,
retirement, revocation, or expiry makes the request fail closed; it cannot produce a manifest whose
declared key differs from its signer. Default production dependency wiring still supplies no signer.

Future persistent registries must make the complete `mutate` operation serializable/atomic. Future
providers must prove private/public correspondence without exporting private material. This phase
contains no network dependency and no retrieval, generation, reranking, support, refusal, Agent, or
Research behavior.
