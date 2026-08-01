# Local production deployment

Copy `.env.example` to an untracked environment file and replace every development
credential. Keep `LOCAL_LLM_BACKEND=extractive`, Ollama, semantic retrieval, reranking,
Agent, Research, and external web access disabled until explicitly approved. Never expose
Ollama or MinIO publicly. Restrict CORS and trusted hosts, use TLS at the ingress, and set
a strong signing secret and non-default database/object-store credentials.

Validate the fail-closed overlay with
`docker compose -f docker-compose.yml -f docker-compose.production.yml config`, build
current source, run `alembic upgrade head` and `alembic check`, then verify distinct
live/readiness endpoints. The overlay requires signing/database/object-store secrets and
explicit CORS/trusted-host configuration, removes public data-service ports, and restores
all optional features to safe defaults. Ollama validation used
operator-provisioned `llama3:latest`, digest
`365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1`,
8.0B Q4_0, context 8192. The repository never pulls a model automatically.
