# Local Production Profile

The recommended local production-like profile is:

```bash
cp .env.example .env
docker compose --profile observability up -d --build
```

Before using it beyond local validation:

- replace all development secrets;
- keep `AGENTIC_RAG_ENABLED=false`, `AGENT_RESEARCH_ENABLED=false`, and external providers disabled
  until an operator explicitly enables them;
- set trusted hosts and CORS to concrete origins;
- verify Prometheus targets and Grafana dashboards;
- run Alembic upgrade/check;
- run backup and restore drills for PostgreSQL and MinIO-compatible storage.

This profile does not deploy to AWS and does not claim cloud production readiness.
