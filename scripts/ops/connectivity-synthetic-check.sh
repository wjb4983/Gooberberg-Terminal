#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:1420}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-10}"
COMMAND_TIMEOUT="${COMMAND_TIMEOUT:-15s}"

check_url() {
  local label="$1"
  local url="$2"

  echo "RUN ${label} url=${url}"
  timeout "$COMMAND_TIMEOUT" curl \
    -fsS \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$REQUEST_TIMEOUT" \
    -o /dev/null \
    "$url"
  echo "PASS ${label}"
}

failures=0
for check in \
  "api-healthz ${API_BASE_URL%/}/healthz" \
  "api-v1-health ${API_BASE_URL%/}/api/v1/health" \
  "frontend ${FRONTEND_URL%/}"
do
  read -r label url <<< "$check"
  if ! check_url "$label" "$url"; then
    failures=$((failures + 1))
    echo "FAIL ${label} url=${url}" >&2
  fi
done

if [[ "$failures" -gt 0 ]]; then
  echo "Local smoke checks failed: ${failures}" >&2
  exit 1
fi

echo "Local smoke checks passed"
