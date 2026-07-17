# API

The OpenAPI document is exposed at `/openapi.json` in non-production environments and an
interactive UI at `/docs`. All workspace APIs require a Bearer token. The token establishes
a default workspace; clients may send `X-Workspace-ID` only for workspaces where the user has
a membership. Uploads return HTTP 202 and a job identifier.
