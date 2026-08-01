# System overview

EKIP is a local-first, multi-tenant knowledge platform. The Next.js frontend calls a
FastAPI API. PostgreSQL stores tenant-scoped metadata and pgvector indexes; Redis brokers
bounded Celery work; MinIO stores source objects and generated artifacts. Ingestion
workers extract and version content. Search performs lexical retrieval with optional
semantic retrieval/reranking, then deterministic sufficiency, conflict, response-state,
claim, and citation validation. Optional Ollama can propose wording only after evidence
authorization; the server remains authoritative and falls back to extractive output.

Controlled Agent and Research use registered server tools and bounded state machines.
They cannot create tools, alter scope, execute a shell, or override authorization.
Prometheus/OpenTelemetry expose bounded operational metadata without document bodies,
provider output, or hidden reasoning.
