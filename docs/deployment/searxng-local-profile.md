# SearXNG Local Profile

Updated on 2026-07-22.

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
```

The Compose service:

- runs only under the `web-search` profile
- does not publish a host port
- uses the internal Docker network
- has a healthcheck
- has conservative CPU and memory limits
- requires no paid API key

If public internet access is unavailable, the platform still passes in internal-only and deterministic-provider modes.
