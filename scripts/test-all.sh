#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_PATHS=(
  apps/api-control-plane/src
  services/orchestrator/src
  services/worker-research/src
  services/worker-training/src
  services/service-inference-live/src
  services/service-portfolio-state/src
  services/service-risk-exec/src
  services/service-data/src
  libs/py/gb_core/src
  libs/py/gb_io/src
  libs/py/gb_clients/src
)

PYTHONPATH="$(IFS=:; echo "${PYTHON_PATHS[*]}")"
export PYTHONPATH

if command -v pytest >/dev/null 2>&1; then
  timeout 120s pytest     apps/api-control-plane/tests     services/orchestrator/tests     services/worker-research/tests     services/worker-training/tests     services/service-inference-live/tests     services/service-portfolio-state/tests     services/service-risk-exec/tests     services/service-data/tests     libs/py/gb_core/tests     libs/py/gb_io/tests     libs/py/gb_clients/tests
else
  echo "pytest is not installed" >&2
  exit 1
fi
