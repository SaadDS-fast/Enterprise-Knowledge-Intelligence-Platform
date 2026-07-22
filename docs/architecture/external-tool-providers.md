# External Tool Providers

Updated on 2026-07-22.

## Modes

The platform remains zero-cost and fully functional with external sources disabled:

```env
AGENT_WEB_SEARCH_ENABLED=false
WEB_SEARCH_PROVIDER=disabled
AGENT_EXTERNAL_APIS_ENABLED=false
```

When disabled, external tools return structured `disabled` results and do not attempt network access.

## Approved Providers

- `disabled`: typed no-network provider.
- `deterministic`: no-network provider for tests and local validation.
- `searxng`: optional self-hosted SearXNG adapter using `SEARXNG_URL`.
- `wikipedia`: approved Wikipedia public API adapter.
- `arxiv`: approved arXiv public API adapter.

No provider accepts arbitrary user URLs, credentials, authorization headers, or proxy settings.

## Result Schema

External results include only provenance and excerpts:

- `source_id`
- `provider`
- `title`
- `canonical_url`
- `excerpt`
- `source_type`
- `retrieval_timestamp`
- `trust_category`
- `rank`
- optional `publication_date`
- optional `authors`

Full fetched pages are not stored. External content is marked as untrusted and remains separate from internal document evidence.

## Planner And Policy

The deterministic plan remains internal-first. The orchestrator may call an external tool only after internal retrieval/diagnosis and only when:

- request has `allow_external_sources=true`
- the relevant feature flag is enabled
- the internal answer path lacks sufficient evidence
- the query is not ambiguous or internally conflicting

Internal organization evidence is preferred over external evidence.
