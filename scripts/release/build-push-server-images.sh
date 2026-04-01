#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-}"
REGISTRY="${2:-ghcr.io/example-org/gooberberg-terminal}"
PUSH_IMAGES="${PUSH_IMAGES:-false}"

if [[ -z "$VERSION" ]]; then
  echo "Error: version argument is required." >&2
  echo "Usage: $0 <semver-version> [registry-prefix]" >&2
  exit 1
fi

IMAGES=(
  "api-control-plane:infra/docker/api.Dockerfile"
  "orchestrator:infra/docker/service.Dockerfile"
  "service-data:infra/docker/service.Dockerfile"
  "service-inference-live:infra/docker/service.Dockerfile"
  "service-portfolio-state:infra/docker/service.Dockerfile"
  "service-risk-exec:infra/docker/service.Dockerfile"
  "worker-research:infra/docker/worker.Dockerfile"
  "worker-training:infra/docker/worker.Dockerfile"
)

for item in "${IMAGES[@]}"; do
  service_name="${item%%:*}"
  dockerfile_path="${item##*:}"
  image_ref="$REGISTRY/$service_name:$VERSION"

  echo "Building $image_ref with $dockerfile_path"
  timeout 30m docker build \
    --file "$dockerfile_path" \
    --tag "$image_ref" \
    .

  if [[ "$PUSH_IMAGES" == "true" ]]; then
    echo "Pushing $image_ref"
    timeout 20m docker push "$image_ref"
  else
    echo "Skipping push for $image_ref (set PUSH_IMAGES=true to enable registry push)."
  fi
done

echo "Server image build/push skeleton complete."
