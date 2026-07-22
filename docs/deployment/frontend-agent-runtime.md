# Frontend Agent Runtime

The Docker frontend build accepts these arguments and environment variables:

```env
NEXT_PUBLIC_AGENTIC_RAG_ENABLED=false
NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED=false
NEXT_PUBLIC_AGENT_EXTERNAL_SOURCES_ENABLED=false
NEXT_PUBLIC_AGENT_POLL_INTERVAL_MS=2000
```

Set the backend flags separately:

```env
AGENTIC_RAG_ENABLED=true
AGENT_RESEARCH_ENABLED=true
```

Because Next.js inlines `NEXT_PUBLIC_*` values during build, rebuild the frontend image after
changing them:

```bash
NEXT_PUBLIC_AGENTIC_RAG_ENABLED=true \
NEXT_PUBLIC_AGENTIC_RESEARCH_ENABLED=true \
docker compose up --build frontend
```

For full browser validation against the Docker stack, enable the gated e2e scenario:

```bash
E2E_AGENTIC_ENABLED=true npm run test:e2e
```

The default disabled configuration continues to expose the original Dashboard, Documents,
Search, Research, and Evaluation routes.
