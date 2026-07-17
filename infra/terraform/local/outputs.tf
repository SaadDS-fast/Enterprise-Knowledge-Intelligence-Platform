output "database_url" {
  value     = "postgresql+asyncpg://ekip:${var.postgres_password}@localhost:${var.postgres_port}/ekip"
  sensitive = true
}

output "redis_url" {
  value = "redis://localhost:${var.redis_port}/0"
}

output "minio_endpoint" {
  value = "http://localhost:${var.minio_api_port}"
}

output "minio_console" {
  value = "http://localhost:${var.minio_console_port}"
}
