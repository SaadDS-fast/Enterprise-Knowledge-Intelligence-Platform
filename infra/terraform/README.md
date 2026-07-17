# Local-only Terraform

This configuration uses the open-source Docker provider to create PostgreSQL/pgvector,
Redis, and MinIO on the developer's own machine. It does not contain AWS, Azure, or
other billable cloud resources. Running it still consumes local compute, disk, and electricity.

```bash
cd local
terraform init
terraform apply
```
