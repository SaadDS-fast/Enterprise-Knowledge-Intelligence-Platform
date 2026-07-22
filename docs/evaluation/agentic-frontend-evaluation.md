# Agentic Frontend Evaluation

Frontend validation covers:

- Feature-flagged route visibility for agent and async research workspaces.
- Internal-only default submissions for agent queries and research jobs.
- Safe rendering of citations, document snippets, conflicts, claims, and timeline summaries.
- Expired artifact URL refresh without storing signed links.
- Existing `/search` and `/research` behavior preservation.
- Gated Playwright coverage for a real browser run through registration, upload, agent query,
  async research creation, and legacy search.

Recommended regression command set:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run test:e2e
npm run build
```

For Docker-backed agentic browser validation, run the stack with both backend and frontend
agentic flags enabled and set `E2E_AGENTIC_ENABLED=true`.
