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
