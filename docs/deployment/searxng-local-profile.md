# SearXNG Local Profile

Updated on 2026-07-23.

SearXNG is optional and not started by the default Docker profile.

Start it explicitly:

```bash
docker compose --profile web-search up -d searxng
```

Enable backend use explicitly:

```env
AGENTIC_RAG_ENABLED=true
AGENT_WEB_SEARCH_ENABLED=true
WEB_SEARCH_PROVIDER=searxng
SEARXNG_URL=http://searxng:8080
SEARXNG_SECRET=replace-with-local-random-value
```

The Compose service:

- runs only under the `web-search` profile
- does not publish a host port
- uses the internal Docker network
- has a healthcheck
- has conservative CPU and memory limits
- requires no paid API key
- mounts `monitoring/searxng/settings.yml` to enable JSON responses for the backend provider

v0.2.1 validation result: direct backend-container request to SearXNG returned HTTP 200 JSON with
26 results for a public Python query. Explicit opt-in `/agent/query` returned status 200,
`external_access_performed=true`, provider `searxng`, 5 external evidence items, and 4 citations.

If public internet access is unavailable, the platform still passes in internal-only and deterministic-provider modes.
