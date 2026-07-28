# Local model security

Only application-defined aliases map to fixed sentence-transformer identifiers. API
callers cannot provide a model, filesystem path, deserialization option, or inference
endpoint. Both model families are CPU-only, lazy-loaded singletons with bounded input,
batch, candidate, result, retry, and timeout controls.

Production inference uses local-files-only loading. Operators provision and verify
weights outside Git; the application does not download them automatically. Model caches,
weights, runtime vectors, extracted documents, databases, and environment files are
ignored and must not be committed.

Workspace, current-version, usable-state, and selected-document predicates run before
embedding comparison and reranking. A tenant's documents are never co-batched with
another tenant's request. Reranking receives only the already-authorized candidate set.
Citations are produced from that same set.

Provider errors are reduced to safe availability categories. Metrics and API diagnostics
contain timing, counts, booleans, and version aliases, but no document content,
embeddings, secrets, hidden reasoning, raw exception messages, or remote addresses.
Lexical retrieval remains available during local model failure when fallback is enabled.

## Live security validation

Explicit provisioning resolved only the fixed allowlist identifiers. Both providers then
passed enforced offline/cache-only inference. Missing caches, an invalid operator alias,
embedding timeout, reranker timeout/unavailability, and incompatible dimension were
tested: requests used deterministic/lexical or fused-score fallback as configured, while
dimension mismatch was rejected before vector comparison. Diagnostics contained no
cache paths, vector values, document bodies, credentials, or raw internal exceptions.

The dependency audit initially identified advisories in transformers 4.57.6. The
optional stack was moved to transformers 5.14.1 and sentence-transformers 5.6.1; the
final pip-audit reported no known vulnerabilities (the private project package itself is
not published on PyPI and was skipped).
