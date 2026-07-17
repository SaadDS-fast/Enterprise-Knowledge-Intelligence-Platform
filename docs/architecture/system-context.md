# System Context

Users access a Next.js frontend and FastAPI API through HTTPS. The API validates identity, authorization, tenant context, and input safety. Interactive queries use the retrieval and LLM layers synchronously. Document ingestion, evaluation, and report generation are asynchronous jobs processed by workers.

Persistent data is split across PostgreSQL/pgvector, Redis, and object storage. Observability and security controls apply across all layers.
