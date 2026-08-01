# Thesis scope boundary

This repository's assurance path is limited to authentication and authorization, one
configured retrieval pass, an optional frozen semantic/reranking configuration, a
deterministic support gate, conflict checking, and either a verified cited answer or a
neutral refusal.

Legacy compatibility states and historical reports remain where removal would break API or
benchmark history. They are not extended, evaluated as product novelty, or used to select
subsequent document retrieval. User interfaces do not expose internal classifications,
score decomposition, retry traces, or technical causes for refusal.

The assurance work does not implement post-insufficiency document retrieval, query changes,
Top-K changes, retriever switching, expanded corpus search, or cause-specific mitigation.

Search and controlled Agent execution use one authorized document retrieval pass. Compatible
legacy fields may remain in API schemas, but Search and Agent interfaces do not display
technical classifications, score decomposition, or internal tool names associated with
those historical paths.
