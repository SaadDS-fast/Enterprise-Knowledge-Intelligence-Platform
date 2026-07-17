# Cost and local development

Default execution uses SQLite or Dockerized PostgreSQL, local filesystem or MinIO storage,
a deterministic hashed embedding model, and extractive answer generation. These components
need no subscription or API key. Ollama is optional and downloads model weights without an
API fee, but requires local compute and storage. AWS, Azure, hosted LLMs, domains, certificates,
and managed monitoring can incur charges only when a user explicitly enables them.

Cloud Terraform was intentionally omitted. The included Terraform configuration manages local Docker containers only.
