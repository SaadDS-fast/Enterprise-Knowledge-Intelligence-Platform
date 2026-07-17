#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t ekip-backend:local backend
docker build --build-arg NEXT_PUBLIC_API_BASE_URL=/api/v1 -t ekip-frontend:local frontend
echo "Load these images into Kind/Minikube before applying the manifests."
