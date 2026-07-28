# Semantic retrieval and reranking

Phase 2 keeps one retrieval path for Search, controlled Agent internal search,
Evaluation, and Research. Candidate generation applies workspace and selected-document
filters in SQL before any text is embedded or reranked. Only chunks from each document's
latest version and usable document states are eligible.

## Pipeline

1. Normalize whitespace in the query without adding entities or changing scope.
2. Score the scoped candidate set with BM25.
3. Embed the normalized query with the configured local sentence model.
4. Reject semantic comparisons whose dimension or embedding version is incompatible.
5. Fuse normalized lexical and cosine scores using operator-configured weights.
6. Apply bounded title, heading, attribute, extraction-quality, and duplicate controls.
7. Rerank at most `RERANKER_TOP_N` candidates and return at most
   `RERANKER_RETURN_K`.
8. If evidence is insufficient, the existing bounded recovery pass expands retrieval
   using the original normalized query and controlled synonym reformulation.

Defaults use 0.45 lexical and 0.55 semantic weight. Semantic retrieval and the
cross-encoder are both disabled until configured. The deterministic provider exists for
tests and continuity fallback; it is not represented as a semantic quality improvement.

Each chunk records provider, allowlisted model alias, dimension, embedding version,
indexing version, and creation time. Retrieval does not compare incompatible or obsolete
vectors. Documents lacking current vector metadata are reported as requiring re-indexing.

Safe diagnostics expose ranks and scores, boosts, scope, timing, versions, and fallback
state. Raw embeddings, model paths, document content, and model internals are never
returned as diagnostics.

## Live validation

The validated local identities are `all-minilm-l6-v2`/`st-v1` at 384 dimensions and
`ms-marco-minilm-l-6-v2`/`ce-v1`. Both lazy singletons loaded and ran from an
operator-provisioned cache with offline enforcement. The re-index path produced exactly
one compatible live vector for every active chunk and did not mix
`deterministic-hash-v1`.

The 2026-07-28 corpus showed that semantic fusion improved Recall@5, but direct
cross-encoder replacement of the fused score harmed top-rank quality. Accordingly the
architecture keeps both features disabled by default; live availability is not itself a
quality rollout decision.

## Calibrated policy

Intent controls diversity, reranking and sufficiency without rewriting entities or
scope. Fusion remains `.45` lexical/`.55` semantic. Cross-encoder scores contribute
`.25` to a blended score; they never replace fused evidence. Absence and ambiguous
intents skip reranking, a margin below `.08` preserves fusion, and failures use the same
fused fallback. Diagnostics expose policy state but no vectors.

The evidence layer requires typed sufficiency and claim-to-span support. Sensitive
numeric labels must match the requested concept, composite answers require distinct
sources, and low-quality evidence cannot become sufficient solely from similarity.
