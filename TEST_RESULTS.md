# Test Results

| Area | Test | Result | Evidence |
| --- | --- | --- | --- |
| Backend | Compilation | Pass | `python -m compileall app tests` |
| Backend | Ruff lint | Pass | `ruff check app tests` |
| Backend | Ruff format | Pass | `ruff format --check app tests` |
| Backend | Module imports | Pass | 159 imported, 0 failures |
| Backend | OpenAPI | Pass | 14 paths generated |
| Backend | Unit/integration/security tests | Pass | 20 passed, 0 failed, 0 skipped, 0 errored |
| Backend | Phase 3/4 tests | Pass | 22 passed, 2 PostgreSQL tests skipped when `POSTGRES_TEST_DATABASE_URL` is unset |
| Backend | Runtime RAG intelligence tests | Pass | 35 passed, 2 PostgreSQL tests skipped |
| Backend | Coverage | Pass | 70% total coverage |
| Backend | Runtime RAG coverage | Pass | 72% total coverage |
| Database | Alembic migration | Pass | Fresh `upgrade head`; `check` no new ops |
| Authentication | Registration/login | Pass | Real HTTP 201/200 |
| Authentication | Invalid login | Pass | Real HTTP 401 |
| Ingestion | TXT | Pass | Upload, completed job, search evidence |
| Ingestion | Markdown | Pass | Upload, completed job, search evidence |
| Ingestion | HTML | Pass | Upload, completed job, search evidence |
| Ingestion | CSV | Pass | Upload, completed job, search evidence |
| Ingestion | Source code | Pass | Upload, completed job, search evidence |
| Ingestion | PDF | Pass | Upload, completed job, search evidence |
| Ingestion | DOCX | Pass | Upload, completed job, search evidence |
| Upload Security | Empty file | Pass | Real HTTP 400 |
| Upload Security | Malformed PDF | Pass | Real HTTP 415 |
| Upload Security | Unsupported extension | Pass | Real HTTP 415 |
| Upload Security | MIME mismatch | Pass | Real HTTP 415 |
| Retrieval | BM25 | Pass | Direct score check |
| Retrieval | Vector | Pass | Direct cosine similarity check |
| Retrieval | Hybrid | Pass | Direct weighted fusion and HTTP search |
| AI | Grounded answer | Pass | Project Atlas answers returned evidence |
| AI | Abstention | Pass | Unrelated Virellia question abstained |
| Tenancy | Cross-tenant document denial | Pass | Other tenant got empty list and 404 detail |
| Tenancy | Cross-tenant search denial | Pass | Other tenant search abstained with 0 evidence |
| Research | Create/list | Pass | Real HTTP 201/200 |
| Evaluation | Create/list | Pass | Real HTTP 201/200 |
| Frontend | npm ci | Pass | Clean install from lockfile |
| Frontend | Lint | Pass | Real ESLint flat config; 0 errors, 1 Next.js metadata warning |
| Frontend | Typecheck | Pass | `npm run type-check` |
| Frontend | Unit/component tests | Pass | `npm run test`; 5 files, 12 tests passed |
| Frontend | Diagnosis component tests | Pass | `npm run test`; 5 files, 19 tests passed |
| Frontend | Build | Pass | `npm run build` |
| Security | Bandit | Pass | No issues |
| Security | pip-audit | Pass | No known vulnerabilities for audited packages |
| Security | npm audit | Pass | 0 vulnerabilities |
| Observability | Metrics | Pass | `/metrics` returned Prometheus output |
| Observability | Config parsing | Pass | Prometheus/Grafana/OTel YAML parsed |
| Docker | Compose config | Not run | Docker CLI unavailable |
| Docker | Compose YAML structure | Pass | Parsed with backend venv PyYAML; 13 services present |
| Docker | Full stack | Not run | Docker CLI unavailable |
