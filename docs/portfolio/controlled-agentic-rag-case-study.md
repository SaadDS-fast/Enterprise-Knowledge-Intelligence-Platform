# Controlled Agentic RAG Case Study

## Problem

Enterprise document assistants must answer from internal evidence without leaking tenant data,
inventing citations, or letting retrieved text control tools.

## Architecture

EKIP combines FastAPI, Next.js, PostgreSQL/pgvector, Redis, Celery, MinIO-compatible storage,
Prometheus, Grafana, and OpenTelemetry. Existing adaptive `/search` remains stable while
agentic workflows live under `/agent`.

## Controlled Agent Design

The agent uses deterministic planning, typed tools, scoped retrieval, evidence verification,
citation validation, conflict detection, safety review, budgets, timeouts, and safe persistence.
Unrestricted agents were rejected because arbitrary shell, SQL, filesystem, HTTP, and multi-agent
delegation would expand the attack surface beyond the product goal.

## Evidence And Evaluation

The platform distinguishes retrieval failure from knowledge absence, verifies claims against
evidence, removes unsupported claims, detects conflicts, and requires citations. Deterministic
evaluation fixtures cover internal-only, multi-source, and research-report workflows.

## Security And Resilience

Tenant/workspace isolation is enforced on documents, runs, research jobs, and artifacts.
Resilience validation covers Redis, MinIO, worker restarts, bounded retries, idempotency, and
artifact duplication checks.

## Limitations

This project has not been deployed to AWS, has not handled live enterprise-scale traffic, and does
not require Ollama or paid services. Optional live SearXNG and Ollama results must be reported only
when actually executed.
