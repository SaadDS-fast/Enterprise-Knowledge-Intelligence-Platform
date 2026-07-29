# Isolated Playwright runtime

Use the repository-owned lifecycle instead of starting Playwright against
ports 3000/8000:

```text
npm run test:e2e:isolated:default
npm run test:e2e:isolated:agentic
npm run test:e2e:isolated:phase2b
```

Each command selects an explicit feature profile, uses alternate ports and a
run-unique Compose project, builds the current source, and creates isolated
PostgreSQL, Redis, and MinIO volumes. It refuses occupied ports. Before tests,
the preflight checks frontend and backend application identities, Git commit,
compatibility ID, readiness, and every relevant public feature flag. A trap
removes containers, network, volumes, traces, screenshots, and reports whether
the test passes or fails.

The default profile disables agentic RAG, research, external APIs, semantic
embeddings, and reranking. The agentic profile enables controlled agentic RAG
and research while retaining the extractive backend and disabling external
APIs, semantic embeddings, and reranking. Neither profile reads feature flags
silently from an existing developer process.
