# Agentic Research API

Agentic research reports are asynchronous and disabled by default.

## Create

`POST /api/v1/agent/research`

```json
{
  "question": "Write a cited launch brief.",
  "document_ids": null,
  "allow_external_sources": false,
  "requested_formats": ["markdown", "pdf", "docx"],
  "max_depth_preset": "standard"
}
```

The accepted response includes a job identifier, status, current state, and whether the request
was an idempotent replay.

## Inspect And Cancel

- `GET /api/v1/agent/research` lists scoped jobs.
- `GET /api/v1/agent/research/{job_id}` returns progress, state, safe report summary fields,
  counts, and sanitized errors.
- `POST /api/v1/agent/research/{job_id}/cancel` requests cancellation for cancellable states.

## Artifacts

`GET /api/v1/agent/research/{job_id}/artifacts` returns scoped artifact metadata and short-lived
download URLs. The frontend does not persist signed URLs. If a URL expires, the client refreshes
artifact metadata and retries once without weakening authorization.
