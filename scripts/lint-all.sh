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

if command -v ruff >/dev/null 2>&1; then
  timeout 120s ruff check .
else
  echo "ruff is not installed" >&2
  exit 1
fi

if command -v black >/dev/null 2>&1; then
  timeout 120s black --check .
else
  echo "black is not installed" >&2
  exit 1
fi

if command -v mypy >/dev/null 2>&1; then
  timeout 120s mypy     apps/api-control-plane/src     services/orchestrator/src     services/worker-research/src     services/worker-training/src     services/service-inference-live/src     services/service-portfolio-state/src     services/service-risk-exec/src     services/service-data/src     libs/py/gb_core/src     libs/py/gb_io/src     libs/py/gb_clients/src
else
  echo "mypy is not installed" >&2
  exit 1
fi
