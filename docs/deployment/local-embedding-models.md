# Local embedding model deployment

Semantic embeddings are local CPU inference, not generative inference. They do not call
Ollama, OpenAI, an arbitrary URL, or a user-selected model path.

## Provisioning

Install the optional runtime explicitly:

```bash
cd backend
.venv/bin/pip install '.[semantic]'
```

Provision one of the allowlisted model aliases into the runtime's Hugging Face cache.
Production sets `local_files_only`, so startup and inference never download a missing
model. The supported 384-dimensional embedding aliases are:

- `all-minilm-l6-v2`
- `multi-qa-minilm-l6-cos-v1`

The supported reranker alias is `ms-marco-minilm-l-6-v2`.

Set `SEMANTIC_EMBEDDINGS_ENABLED=true`, the model alias and dimension, then optionally
set `RERANKER_ENABLED=true` and its model alias. Keep the device as `cpu`. Restart the
backend and ingestion worker, check `/api/v1/health/ready`, and re-index existing
documents with `POST /api/v1/documents/{document_id}/reindex` using an
`Idempotency-Key`.

For Docker, build affected Python images with
`--build-arg INSTALL_SEMANTIC_MODELS=true`, and mount a read-only, operator-provisioned
model cache inside the backend and ingestion worker. Do not publish that cache or any
model service port. Docker Desktop on macOS must mount a Docker-accessible host path;
Linux uses the equivalent bind mount or a pre-populated private volume. A backend run
directly on the host uses its own local cache.

Model caches belong outside Git. If a model is missing, lexical/deterministic fallback
keeps retrieval available when fallback is enabled. No network connection is required
during provisioned inference.
