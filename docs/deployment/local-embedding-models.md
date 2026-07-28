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

## Validated provisioning recipe

Use a dedicated operator cache outside the checkout (for example,
`$XDG_CACHE_HOME/ekip-models`; do not place it in Git):

```bash
cd backend
.venv/bin/pip install '.[semantic]'
HF_HOME=/operator/cache/ekip-models HF_HUB_DISABLE_XET=1 .venv/bin/python -c \
  "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

The validated package set was sentence-transformers 5.6.1, transformers 5.14.1,
huggingface-hub 1.25.1, and torch 2.13.0. Validate cache-only operation with
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`. Runtime loaders always request local files;
missing cache entries fall back safely and do not trigger downloads. Host-direct
backend/worker connectivity was validated; container deployments must bind the same
cache read-only into every model-using process. Re-index after any provider, alias,
dimension, or embedding-version change.
