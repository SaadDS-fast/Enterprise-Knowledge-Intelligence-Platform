# Validation Report

Validated on **2026-07-17** for the complete local-first EKIP source archive.

## Passed checks

- Python compilation for `backend/app` and all worker packages
- Import of 168 backend application modules with zero import failures
- Backend automated test suite: **17 passed**
- Ruff static analysis across backend, tests, and workers: **passed**
- End-to-end integration coverage for registration, authentication, document upload,
  inline ingestion, grounded retrieval, and answer generation
- Security tests for upload validation and cross-tenant isolation
- OpenAPI contract generation: **14 API paths**
- Frontend TypeScript validation: **passed**
- Next.js optimized production build: **passed**
- npm production dependency audit: **0 reported vulnerabilities**
- YAML parsing: **31 files passed**
- Terraform HCL parsing: **4 local-only files passed**
- Archive integrity test: performed after packaging

## Validation boundaries

No responsible engineering process can guarantee a zero percent chance of defects on every
operating system, CPU architecture, Docker version, browser, or future dependency release.
This package minimizes that risk through pinned frontend dependencies, constrained backend
dependencies, automated tests, static analysis, production builds, and deterministic local
fallback behavior.

The execution environment did not provide Docker, Terraform, or kubectl command-line tools.
Therefore, Compose, local Terraform, and Kubernetes definitions were parsed for syntax but
were not launched here. The application itself was exercised using SQLite and local object
storage, which are the intended lightweight zero-fee validation mode.

## Cost boundary

The default implementation requires no paid cloud account or paid model API. It supports a
deterministic extractive answer provider locally. PostgreSQL/pgvector, Redis, MinIO, Ollama,
Prometheus, Grafana, Docker, FastAPI, and Next.js are optional/open-source local components.
The user's hardware, electricity, storage, and internet access remain real external costs.
Commercial OpenAI/Azure adapters exist only as optional integrations and are disabled by
default. No AWS or Azure infrastructure is defined in the included Terraform configuration.
