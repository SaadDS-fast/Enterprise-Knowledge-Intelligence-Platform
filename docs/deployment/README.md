# Deployment

Use Docker Compose for the supported zero-cost local deployment. Kubernetes manifests target
local clusters such as Kind or Minikube and expect locally built images named
`ekip-backend:local` and `ekip-frontend:local`. No cloud deployment is included because the
project's current constraint forbids implementations that require paid infrastructure.
