# Answer Passport production integration boundary

```text
unchanged Search lifecycle
  -> one configured retrieval pass
  -> static support/conflict gate
  -> optional verified generation
  -> canonical final response
  -> internal projection adapter
  -> eligibility guard
  -> injected signer (at most once)
  -> internal issuance result
```

The only production hook wraps the completed `search_and_answer` lifecycle. The original lifecycle
returns first; the post-support step cannot change its answer, citations, support state or refusal.
The disabled and missing-signer paths do not construct a projection.

Dependency direction is intentionally one-way. `app.passport.issuance` may read production response
and database models. Phase 1 canonicalization, hashing, JWS, schema, verifier and CLI remain free of
retrieval, generation, orchestration, persistence and network imports. The integration module has
no retriever, LLM, reranker, embedding, Agent, Research or network dependency.

Standard Search is compatible. Agent fallback that calls Standard Search retains the unchanged
Search hook, but independent Agent terminal answers are ineligible. Research calls Standard Search
internally but its assembled report is not a passport projection and receives no report passport.
This avoids duplicated provider hooks and schema weakening.

Issuance failure is separate from grounding status. It never causes another retrieval/generation,
changes a support decision, removes citations, or describes the supported answer as ungrounded.
There is no public surface or persistent artifact in Phase 2.
