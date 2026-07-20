# Enterprise Gap Analysis

Created on 2026-07-20 from branch `feature/enterprise-completion`, based on validated commit `1e4f3d8`.

## Source Documents

- `KNOWN_LIMITATIONS.md`
- `TEST_RESULTS.md`
- `VALIDATION_REPORT.md`
- `README.md`
- `PROJECT_TREE.txt`
- Direct inspection of backend, frontend, infrastructure, worker, monitoring, and security code paths.

## Executive Summary

The repository is a functional local MVP with real FastAPI routes, JWT authentication, workspace tenancy, document upload, local object storage, ingestion, deterministic local embeddings, hybrid retrieval, evidence sufficiency, extractive answer generation, research/evaluation endpoints, frontend pages, metrics, and source-level validation.

The main enterprise gaps are integration depth and operational proof, not basic feature presence. PostgreSQL/pgvector, Redis, MinIO, Celery, Prometheus, Grafana, and OpenTelemetry are configured for Docker but were not runtime-validated together. Frontend linting is currently a no-op, frontend component tests are missing, Redis cache use is not integrated into request flows, vector retrieval is in-process rather than database-native pgvector search, and several security, lifecycle, agent, and MLOps modules are present but only lightly exercised.

## Runtime Flow Map

### Implemented Local MVP Flow

```text
Next.js frontend
-> frontend/lib/api.ts
-> FastAPI app in backend/app/main.py
-> API router under backend/app/api/v1
-> JWT authentication and workspace context dependencies
-> Service layer
-> SQLAlchemy async session
-> SQLite by default, PostgreSQL when DATABASE_URL is set
-> Local object storage by default
-> Inline FastAPI background ingestion by default
-> Loaders, normalization, chunking, deterministic embeddings
-> Chunk rows with embedding arrays
-> In-process BM25 + cosine similarity + lexical reranker
-> Evidence sufficiency and abstention
-> Local extractive LLM provider by default
-> Structured response to frontend
-> Request logs and Prometheus metrics
```

### Docker-Oriented Flow

```text
Next.js container
-> FastAPI container
-> JWT authentication and workspace tenancy
-> SQLAlchemy async session
-> PostgreSQL container with pgvector image
-> MinIO object storage
-> Celery dispatch through Redis broker
-> ingestion-worker container
-> Chunk and embedding persistence
-> Retrieval from database rows, ranked in application memory
-> Evidence verification
-> Local extractive generation, optional Ollama profile
-> Prometheus scrape and optional OpenTelemetry collector/Grafana profiles
```

### Gaps In Intended Enterprise Flow

```text
Redis cache/cache policies exist but are not integrated into major read paths.
pgvector extension can be created, but retrieval does not use native vector indexes or similarity SQL.
MinIO and Celery paths are configured but not runtime-validated in the latest report.
Audit-event persistence exists as a repository/model but is not broadly wired into user workflows.
OpenTelemetry config exists but tracing was not runtime-launched in validation.
Frontend has pages and API calls but lacks real linting and component/browser tests.
```

## Feature Classification

| Feature | Classification | Evidence | Gap / Next Action |
| --- | --- | --- | --- |
| Account registration, login, invalid login | Already implemented and tested | `backend/app/api/v1/auth.py`, `TEST_RESULTS.md` | Add frontend tests and stronger session handling. |
| JWT auth and password hashing | Already implemented and tested | `backend/app/security/authentication.py` | Add token revocation/refresh strategy before production. |
| Workspace tenancy | Already implemented and tested | API dependencies, tenancy tests, `TEST_RESULTS.md` | Expand audit logging and policy tests. |
| Role-aware document actions | Implemented but incomplete | `backend/app/documents/permissions.py`, `PermissionGuard.tsx` | Frontend guard is auth-only; backend role policies need broader workflow coverage. |
| Document upload | Already implemented and tested | `document_service.py`, upload security tests | Add malware scanner integration beyond placeholder clean scan. |
| File validation | Already implemented and tested | `file_validation.py`, security tests | Add archive handling and deeper content-type detection if needed. |
| Malware scanning | Placeholder | `backend/app/security/malware_scan.py` | Integrate ClamAV or another open-source scanner with fail-closed production mode. |
| Local object storage | Already implemented and tested | `LocalObjectStorage`, HTTP validation | Add retention/lifecycle tests. |
| MinIO object storage | Implemented but not runtime-tested | `MinioObjectStorage`, Docker Compose | Run Docker stack validation and add integration test profile. |
| S3/Azure storage | Intentionally deferred optional paid integrations | `s3.py`, `azure_blob.py` | Keep disabled by default; validate only when explicitly configured. |
| TXT/Markdown/HTML/CSV/source/PDF/DOCX loaders | Already implemented and tested | Loader modules, `TEST_RESULTS.md` | Add malformed and large-file cases. |
| Ingestion pipeline | Already implemented and tested locally | `backend/app/ingestion/pipeline.py` | Runtime-test Celery worker path. |
| Celery worker path | Implemented but not integrated in validation | `backend/app/jobs/service.py`, `queue.py`, `tasks.py`, Docker Compose | Run with Redis and worker container; add smoke tests. |
| Worker packages under `workers/*` | Implemented but not integrated | `workers/ingestion_worker`, `workers/evaluation_worker`, `workers/report_worker` | Consolidate with backend Celery tasks or document boundaries. |
| PostgreSQL runtime | Implemented but not runtime-tested | Docker Compose and SQLAlchemy config | Validate with Docker PostgreSQL instead of SQLite. |
| pgvector extension | Implemented but incomplete | `init_database()` creates extension on PostgreSQL | Add migration-managed extension and vector indexes. |
| Native pgvector retrieval | Missing | `hybrid_retriever.py` loads rows and ranks in memory | Use SQL vector similarity and indexes for production scale. |
| Deterministic local embeddings | Already implemented and tested | `rag/embeddings.py`, retrieval tests | Replace or augment with optional local embedding model provider. |
| Local embedding model provider | Missing | No sentence-transformers/model runtime path found | Add optional open-source model provider with deterministic fallback. |
| BM25 retrieval | Already implemented and tested | `rag/bm25.py`, tests | Consider per-workspace/document indexing for scale. |
| Hybrid retrieval | Already implemented and tested | `rag/hybrid_retriever.py`, `TEST_RESULTS.md` | Move semantic candidate generation to pgvector. |
| Reranking | Implemented but incomplete | `rag/reranker.py` lexical scoring | Add optional local cross-encoder reranker. |
| Evidence sufficiency and abstention | Already implemented and tested | `rag/evidence.py`, abstention regression test | Add adversarial and multi-document evidence tests. |
| Prompt security | Implemented but incomplete | `security/prompt_security.py` | Add tests for prompt injection patterns and tool-use boundaries. |
| Local extractive generation | Already implemented and tested | `llm/providers/local.py`, validation flow | Add quality evaluation baselines. |
| Ollama provider | Implemented but not runtime-tested | `LocalLLMBackend.OLLAMA`, Docker Compose profile | Validate against a locally pulled model when available. |
| OpenAI/Azure providers | Intentionally deferred optional paid integrations | Provider adapters and config validation | Keep optional and disabled by default. |
| Research briefs | Already implemented and tested | `research_service.py`, API tests | Improve async execution and evaluation of citations. |
| Evaluation runs | Already implemented and tested | `evaluation_service.py`, `evaluation/runner.py` | Add dataset management and regression history. |
| MLOps experiment tracking | Missing | No persistent model/eval registry found | Add local evaluation dataset/version/result storage. |
| Redis cache client | Implemented but not integrated | `cache/client.py`, `cache/policies.py` | Wire into selected read paths with tests and graceful fallback. |
| Rate limiting | Implemented but incomplete | `api/dependencies/rate_limit.py` | Verify persistence/distribution with Redis, not just local process behavior. |
| Audit-event model/repository | Implemented but incomplete | `audit_events.py`, DB model | Wire to auth, upload, search, admin actions. |
| Request IDs and structured logs | Already implemented and tested | middleware and validation report | Add trace correlation in frontend/API responses. |
| Prometheus metrics | Already implemented and tested | `/metrics`, validation report | Add custom business/retrieval/worker metrics. |
| Grafana dashboards | Implemented but not runtime-tested | provisioning files | Launch and verify dashboards in Docker profile. |
| OpenTelemetry tracing | Implemented but not runtime-tested | `observability/tracing.py`, collector config | Runtime-test traces with collector. |
| Security headers and CORS controls | Implemented and tested by source validation | middleware/config | Add browser/security tests. |
| SSRF and egress policy modules | Placeholder / low coverage | `security/ssrf.py`, `egress_policy.py` | Integrate where external fetch tools are added. |
| Redaction and retention modules | Placeholder / low coverage | `security/redaction.py`, `documents/retention.py` | Wire into ingestion/export/delete workflows. |
| Frontend pages | Implemented but incomplete | Next.js app routes and components | Add real lint, tests, accessibility states, and browser automation. |
| Frontend linting | Missing | `package.json` lint is a no-op | Replace with real ESLint flat config. |
| Frontend unit/component testing | Missing | No test runner dependencies/config | Add Vitest, React Testing Library, jsdom tests. |
| Frontend browser automation | Missing | Validation report | Add Playwright or equivalent later if zero-cost local deps are acceptable. |
| Docker Compose syntax | Implemented but not runtime-tested | `docker-compose.yml`, YAML parsed | Run `docker compose config` and full stack where Docker exists. |
| Kubernetes manifests | Implemented but not runtime-tested | `infra/kubernetes` | Validate with kubeconform/kustomize when tools are available. |
| Terraform local config | Implemented but not runtime-tested | `infra/terraform/local` | Validate with `terraform validate` when tool is available. |
| Documentation baseline | Already implemented and tested by inspection | README, validation reports, runbooks | Keep updated phase by phase. |

## Phase Backlog

1. Replace the frontend no-op lint script with real ESLint configuration.
2. Add frontend unit/component tests for auth, protected route behavior, upload validation states, search/evidence rendering, loading/error states, and permission guard.
3. Make PostgreSQL/pgvector the production data path by migration-managing the vector extension and adding native vector search/index support while keeping SQLite-compatible tests.
4. Runtime-validate Redis, MinIO, Celery, PostgreSQL/pgvector, and observability profiles on a Docker-capable machine.
5. Integrate Redis cache and distributed rate limiting where they provide measurable value.
6. Replace placeholder security hooks with open-source local implementations or explicit fail-closed production checks.
7. Add local model-provider options for embeddings and reranking without making paid APIs mandatory.
8. Expand evaluation/MLOps storage so retrieval, generation, abstention, and citation quality can be tracked over time.

## Zero-Cost Boundary

The default path remains zero-cost: FastAPI, Next.js, SQLite/local storage for lightweight development, PostgreSQL/pgvector/Redis/MinIO/Celery in Docker, deterministic embeddings, extractive local answers, Prometheus, Grafana, and OpenTelemetry. Paid providers are optional adapters and must remain disabled unless explicit configuration is supplied.
