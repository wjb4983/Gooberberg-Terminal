#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<USAGE
Usage: $(basename "$0") <candidate-id> [report-path]

Runs the minimal release-candidate validation suite with hard per-check timeouts.
Timeout is treated as a failure and the release candidate must be rerun after fix.
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

candidate_id="$1"
report_path="${2:-dist/release/${candidate_id}-release-suite-report.json}"

mkdir -p "$(dirname "$report_path")"

checks=(
  "data_contracts|300|pytest apps/api-control-plane/tests/test_contract_routes_and_dispatch.py apps/api-control-plane/tests/test_task_catalog_schema.py"
  "leakage_checks|300|pytest services/worker-training/tests/test_data_splits_advanced.py"
  "walk_forward_stability|420|pytest services/worker-training/tests/test_metric_engine.py"
  "execution_simulation_sanity|300|pytest libs/py/gb_core/tests/test_paper_execution.py services/service-risk-exec/tests/test_execution_engine_models.py"
  "risk_limit_checks|300|pytest libs/py/gb_core/tests/test_risk_monitors.py services/service-risk-exec/tests/test_runtime_guard.py apps/api-control-plane/tests/test_risk.py"
)

results_json=""
overall_status="PASS"
failed_checks=()

run_check() {
  local name="$1"
  local timeout_s="$2"
  local cmd="$3"

  echo "[release-suite] Running ${name} (timeout=${timeout_s}s)"
  set +e
  output="$(timeout --preserve-status "${timeout_s}" bash -lc "$cmd" 2>&1)"
  exit_code=$?
  set -e

  local status="PASS"
  local reason=""
  if [[ $exit_code -eq 124 || $exit_code -eq 137 ]]; then
    status="FAIL"
    reason="timeout"
    overall_status="FAIL"
    failed_checks+=("$name(timeout)")
  elif [[ $exit_code -ne 0 ]]; then
    status="FAIL"
    reason="nonzero_exit"
    overall_status="FAIL"
    failed_checks+=("$name(failed)")
  fi

  local output_escaped
  output_escaped="$(printf '%s' "$output" | python -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"

  if [[ -n "$results_json" ]]; then
    results_json+=","
  fi
  results_json+="{\"check\":\"${name}\",\"timeout_seconds\":${timeout_s},\"status\":\"${status}\",\"reason\":\"${reason}\",\"exit_code\":${exit_code},\"output\":${output_escaped}}"
}

for item in "${checks[@]}"; do
  IFS='|' read -r name timeout_s cmd <<<"$item"
  run_check "$name" "$timeout_s" "$cmd"
done

rerun_required=false
if [[ "$overall_status" == "FAIL" ]]; then
  rerun_required=true
fi

timestamp_utc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cat > "$report_path" <<JSON
{
  "candidate_id": "${candidate_id}",
  "generated_at_utc": "${timestamp_utc}",
  "overall_status": "${overall_status}",
  "rerun_required_after_fix": ${rerun_required},
  "checks": [${results_json}]
}
JSON

if [[ "$overall_status" == "PASS" ]]; then
  echo "[release-suite] PASS: all checks passed"
  echo "[release-suite] report: $report_path"
  exit 0
fi

echo "[release-suite] FAIL: ${failed_checks[*]}"
echo "[release-suite] Timeout is treated as a failure; rerun is required after fix."
echo "[release-suite] report: $report_path"
exit 1
