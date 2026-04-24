#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="apps/api-control-plane/src:${PYTHONPATH:-}"

echo "[unit] retry/timeout/circuit transitions"
timeout 120s pytest apps/api-control-plane/tests/test_ws.py -k 'heartbeat'

echo "[integration] health/auth/ws/replay contracts"
timeout 180s pytest \
  apps/api-control-plane/tests/test_health.py \
  apps/api-control-plane/tests/test_auth.py \
  apps/api-control-plane/tests/test_ws.py

echo "[e2e] onboarding + diagnostics + recovery actions (contract smoke)"
timeout 180s pytest \
  apps/api-control-plane/tests/test_health.py::test_health_endpoint_returns_placeholder_dependency_status \
  apps/api-control-plane/tests/test_auth.py::test_health_endpoint_stays_public \
  apps/api-control-plane/tests/test_ws.py::test_websocket_replays_from_last_seq_and_reports_complete
