variable "project_name" {
  description = "Prefix for local Docker resources."
  type        = string
  default     = "ekip"
}

variable "postgres_port" {
  type    = number
  default = 5432
}

variable "redis_port" {
  type    = number
  default = 6379
}

variable "minio_api_port" {
  type    = number
  default = 9000
}

variable "minio_console_port" {
  type    = number
  default = 9001
}

variable "postgres_password" {
  type      = string
  sensitive = true
  default   = "ekip-local-only"
}

variable "minio_password" {
  type      = string
  sensitive = true
  default   = "minio-local-only"
}
