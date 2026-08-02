# Passport key-lifecycle architecture

The public metadata registry and private signing provider are separate interfaces. Registry atomic
mutation owns uniqueness, historical retention, relationship integrity, and the zero-or-one-active
invariant. The provider exposes only public-key lookup and signing by opaque key ID; it exposes no
raw private key, seed, serialization, credential, or filesystem operation.

Phase 2 may use `LifecyclePassportSigner`. Resolution reads one atomic snapshot. Signing then
revalidates and invokes the provider while holding the issuer registry lock. Provider-sign
completion is the sign linearization point: if signing wins, the transition waits; if a terminal
transition commits first, signing fails closed. It never switches to a successor. Default
production wiring supplies no signer.

Registry publication linearizes activation, retirement, and revocation. Rotation publishes
successor activation and predecessor retirement together. Versioned snapshot acquisition
linearizes trust generation. Lock order is registry before provider; the provider never enters the
registry, preventing a lock cycle.

Future persistent registries must make mutation, sign exclusion, lifecycle revision allocation,
and versioned snapshots serializable across processes. Audit delivery is observational after
commit: sink failure cannot roll back or misreport a committed transition. Future providers must
prove private/public correspondence without exporting private material. This phase
contains no network dependency and no retrieval, generation, reranking, support, refusal, Agent, or
Research behavior.
