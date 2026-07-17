provider "docker" {}

resource "docker_network" "ekip" {
  name = "${var.project_name}-network"
}

resource "docker_volume" "postgres" {
  name = "${var.project_name}-postgres"
}

resource "docker_volume" "redis" {
  name = "${var.project_name}-redis"
}

resource "docker_volume" "minio" {
  name = "${var.project_name}-minio"
}

resource "docker_image" "postgres" {
  name = "pgvector/pgvector:pg16"
}

resource "docker_image" "redis" {
  name = "redis:7-alpine"
}

resource "docker_image" "minio" {
  name = "minio/minio:latest"
}

resource "docker_container" "postgres" {
  name    = "${var.project_name}-postgres"
  image   = docker_image.postgres.image_id
  restart = "unless-stopped"

  networks_advanced {
    name = docker_network.ekip.name
  }

  env = [
    "POSTGRES_DB=ekip",
    "POSTGRES_USER=ekip",
    "POSTGRES_PASSWORD=${var.postgres_password}",
  ]

  ports {
    internal = 5432
    external = var.postgres_port
  }

  volumes {
    volume_name    = docker_volume.postgres.name
    container_path = "/var/lib/postgresql/data"
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ekip -d ekip"]
    interval = "5s"
    timeout  = "5s"
    retries  = 20
  }
}

resource "docker_container" "redis" {
  name    = "${var.project_name}-redis"
  image   = docker_image.redis.image_id
  command = ["redis-server", "--appendonly", "yes"]
  restart = "unless-stopped"

  networks_advanced {
    name = docker_network.ekip.name
  }

  ports {
    internal = 6379
    external = var.redis_port
  }

  volumes {
    volume_name    = docker_volume.redis.name
    container_path = "/data"
  }

  healthcheck {
    test     = ["CMD", "redis-cli", "ping"]
    interval = "5s"
    timeout  = "3s"
    retries  = 20
  }
}

resource "docker_container" "minio" {
  name    = "${var.project_name}-minio"
  image   = docker_image.minio.image_id
  command = ["server", "/data", "--console-address", ":9001"]
  restart = "unless-stopped"

  networks_advanced {
    name = docker_network.ekip.name
  }

  env = [
    "MINIO_ROOT_USER=minioadmin",
    "MINIO_ROOT_PASSWORD=${var.minio_password}",
  ]

  ports {
    internal = 9000
    external = var.minio_api_port
  }

  ports {
    internal = 9001
    external = var.minio_console_port
  }

  volumes {
    volume_name    = docker_volume.minio.name
    container_path = "/data"
  }
}
