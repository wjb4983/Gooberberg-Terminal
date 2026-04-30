#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHONPATH="apps/api-control-plane/src:libs/py/gb_core/src"
export PYTHONPATH

timeout 60s pytest libs/py/gb_core/tests/test_fault_injection_resilience.py

timeout 180s pytest libs/py/gb_core/tests apps/api-control-plane/tests/test_replay_parity_faults.py -k 'replay or fault or circuit'

timeout 300s pytest apps/api-control-plane/tests/test_replay_parity_faults.py

timeout 300s pytest libs/py/gb_core/tests/test_fault_injection_resilience.py
