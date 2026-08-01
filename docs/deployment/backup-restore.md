# Backup and restore

Use a maintenance window and run-scoped paths with restrictive permissions. Capture a
PostgreSQL custom-format dump and a versioned MinIO mirror. Record checksums and the
application commit. Restore into a new isolated database and private bucket, apply
migrations, then verify tenant/workspace/document counts, active chunks, object presence,
and claim-linked citations before changing traffic.

Never commit backups. Delete disposable copies after verification. A database-only backup
is incomplete: object data and its checksum inventory must be restored together. Roll back
the application to `736a402` only with a schema compatible with that commit.
