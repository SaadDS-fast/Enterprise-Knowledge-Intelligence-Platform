# Backup And Recovery

Backup targets:

- PostgreSQL database;
- MinIO-compatible object storage bucket;
- deployment configuration and migrations;
- Grafana dashboards and Prometheus rules.

Recovery drill:

1. Restore database snapshot.
2. Restore object storage.
3. Run Alembic upgrade/check.
4. Verify document search, agent run read, research job read, artifact listing, and artifact
   download authorization.
5. Confirm no cross-tenant evidence or artifact leakage.

Do not restore generated reports into Git.
