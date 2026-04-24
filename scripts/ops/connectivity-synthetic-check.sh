#!/usr/bin/env bash
set -euo pipefail

TOPOLOGY="${1:-${TOPOLOGY:-}}"
BASE_URL="${2:-${BASE_URL:-}}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-10}"

if [[ -z "$TOPOLOGY" || -z "$BASE_URL" ]]; then
  echo "usage: $0 <topology> <base_url>" >&2
  exit 2
fi

curl_code() {
  timeout "${REQUEST_TIMEOUT}s" curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "$CONNECT_TIMEOUT" "$@"
}

check_health() {
  local code
  code="$(curl_code "$BASE_URL/healthz")"
  [[ "$code" == "200" ]]
}

check_bad_token() {
  local code
  code="$(curl_code -H 'Authorization: Bearer gb-invalid-token' "$BASE_URL/api/v1/models/deployments")"
  [[ "$code" == "401" || "$code" == "403" ]]
}

check_backend_down_contract() {
  local down_url
  down_url="${BACKEND_DOWN_URL:-http://127.0.0.1:1}"
  if timeout "${REQUEST_TIMEOUT}s" curl -sS -o /dev/null --connect-timeout "$CONNECT_TIMEOUT" "$down_url/healthz"; then
    return 1
  fi
  return 0
}

check_queue_contract() {
  local payload
  payload="$(timeout "${REQUEST_TIMEOUT}s" curl -sS --connect-timeout "$CONNECT_TIMEOUT" "$BASE_URL/api/v1/health/queue")"
  python - <<'PY' "$payload"
import json,sys
p=json.loads(sys.argv[1])
if 'status' not in p:
    raise SystemExit(1)
raise SystemExit(0)
PY
}

check_ws_contract() {
  local ws_url
  ws_url="${BASE_URL%/}/ws"
  local code
  code="$(curl_code -H 'Connection: Upgrade' -H 'Upgrade: websocket' "$ws_url")"
  [[ "$code" =~ ^(101|400|426)$ ]]
}

run_check() {
  local name="$1"
  if "$name"; then
    echo "PASS ${name} topology=${TOPOLOGY}"
  else
    echo "FAIL ${name} topology=${TOPOLOGY}" >&2
    return 1
  fi
}

failures=0
for fn in check_health check_bad_token check_backend_down_contract check_queue_contract check_ws_contract; do
  if ! run_check "$fn"; then
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -gt 0 ]]; then
  echo "Synthetic checks failed: ${failures}" >&2
  exit 1
fi

echo "Synthetic checks passed for topology=${TOPOLOGY} base_url=${BASE_URL}"
