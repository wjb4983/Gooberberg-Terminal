#!/usr/bin/env bash
set -euo pipefail

TOPOLOGY="${1:-${TOPOLOGY:-}}"
BASE_URL="${2:-${BASE_URL:-}}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
CONNECT_TIMEOUT="${CONNECT_TIMEOUT:-5}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-10}"
KNOWN_FAMILY="${KNOWN_FAMILY:-gpt-4o}"

MODEL_CONFIGS_MIN_PAYLOAD='{"name":"synthetic-smoke-config","provider":"openai","model_family":"gpt-4o","enabled":true}'

if [[ -z "$TOPOLOGY" || -z "$BASE_URL" ]]; then
  echo "usage: $0 <topology> <base_url>" >&2
  exit 2
fi

curl_capture() {
  local method="$1"
  local url="$2"
  local payload="${3:-}"
  local auth_header="${4:-}"

  local tmp_body
  tmp_body="$(mktemp)"

  local -a args
  args=(
    -sS
    -X "$method"
    -o "$tmp_body"
    -w '%{http_code}'
    --connect-timeout "$CONNECT_TIMEOUT"
    --max-time "$REQUEST_TIMEOUT"
    "$url"
  )

  if [[ -n "$auth_header" ]]; then
    args=(-H "$auth_header" "${args[@]}")
  fi
  if [[ -n "$payload" ]]; then
    args=(-H 'Content-Type: application/json' --data "$payload" "${args[@]}")
  fi

  local code
  if ! code="$(timeout "${REQUEST_TIMEOUT}s" curl "${args[@]}")"; then
    code="000"
  fi

  local snippet
  snippet="$(tr '\n' ' ' < "$tmp_body" | cut -c1-240)"
  rm -f "$tmp_body"

  printf '%s\n%s\n' "$code" "$snippet"
}

endpoint_probe() {
  local label="$1"
  local method="$2"
  local path="$3"
  local expected_regex="$4"
  local payload="${5:-}"

  local auth_header=""
  if [[ -n "$AUTH_TOKEN" ]]; then
    auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  fi

  mapfile -t result < <(curl_capture "$method" "${BASE_URL%/}${path}" "$payload" "$auth_header")
  local code="${result[0]}"
  local snippet="${result[1]:-}"

  echo "${label} method=${method} path=${path} status=${code} body_snippet=${snippet}"
  [[ "$code" =~ $expected_regex ]]
}

check_health() {
  endpoint_probe "healthz" "GET" "/healthz" '^200$'
}

check_bad_token() {
  mapfile -t result < <(curl_capture "GET" "${BASE_URL%/}/api/v1/models/deployments" "" "Authorization: Bearer gb-invalid-token")
  local code="${result[0]}"
  local snippet="${result[1]:-}"
  echo "bad-token method=GET path=/api/v1/models/deployments status=${code} body_snippet=${snippet}"
  [[ "$code" == "401" || "$code" == "403" ]]
}

check_backend_down_contract() {
  local down_url
  down_url="${BACKEND_DOWN_URL:-http://127.0.0.1:1}"
  if timeout "${REQUEST_TIMEOUT}s" curl -sS -o /dev/null --connect-timeout "$CONNECT_TIMEOUT" --max-time "$REQUEST_TIMEOUT" "$down_url/healthz"; then
    return 1
  fi
  return 0
}

check_queue_contract() {
  mapfile -t result < <(curl_capture "GET" "${BASE_URL%/}/api/v1/health/queue")
  local code="${result[0]}"
  local payload="${result[1]:-}"
  echo "queue-contract method=GET path=/api/v1/health/queue status=${code} body_snippet=${payload}"
  [[ "$code" == "200" ]] || return 1
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
  mapfile -t result < <(curl_capture "GET" "$ws_url" "" "Connection: Upgrade")
  local code="${result[0]}"
  local snippet="${result[1]:-}"
  echo "ws-contract method=GET path=/ws status=${code} body_snippet=${snippet}"
  [[ "$code" =~ ^(101|400|426)$ ]]
}

check_model_configs_get() {
  endpoint_probe "model-configs-get" "GET" "/api/v1/model-configs" '^(200|401|403)$'
}

check_model_configs_post() {
  endpoint_probe "model-configs-post" "POST" "/api/v1/model-configs" '^(200|201|202|400|401|403|409|422)$' "$MODEL_CONFIGS_MIN_PAYLOAD"
}

check_catalog_get() {
  endpoint_probe "catalog-get" "GET" "/api/v1/models/deployments/catalog" '^(200|401|403)$'
}

check_catalog_family_get() {
  endpoint_probe "catalog-family-get" "GET" "/api/v1/models/deployments/catalog/${KNOWN_FAMILY}" '^(200|401|403|404)$'
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
for fn in \
  check_health \
  check_bad_token \
  check_backend_down_contract \
  check_queue_contract \
  check_ws_contract \
  check_model_configs_get \
  check_model_configs_post \
  check_catalog_get \
  check_catalog_family_get
do
  if ! run_check "$fn"; then
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -gt 0 ]]; then
  echo "Synthetic checks failed: ${failures}" >&2
  exit 1
fi

echo "Synthetic checks passed for topology=${TOPOLOGY} base_url=${BASE_URL}"
