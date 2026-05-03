#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ops/lib.sh
source "$ROOT_DIR/scripts/ops/lib.sh"

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-config/env/.env}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"
COMPOSE_PROFILES_RAW="${COMPOSE_PROFILES:-}"
COMPOSE_SERVICES_RAW="${COMPOSE_SERVICES:-}"
if [[ -f "$ROOT_DIR/$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ROOT_DIR/$ENV_FILE"
  set +a
fi
API_BIND_IP="${API_BIND_IP:-0.0.0.0}"
API_BIND_PORT="${API_BIND_PORT:-8000}"
API_HEALTH_HOST="${API_BIND_IP}"
if [[ "$API_HEALTH_HOST" == "0.0.0.0" ]]; then
  API_HEALTH_HOST="127.0.0.1"
fi
API_HEALTH_URL="${API_HEALTH_URL:-http://${API_HEALTH_HOST}:${API_BIND_PORT}/healthz}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-20m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-90}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"

[[ -n "${GB_API_AUTH_TOKEN:-}" ]] || die "$EXIT_USAGE" 'GB_API_AUTH_TOKEN is required.'
[[ -n "${POSTGRES_PASSWORD:-}" ]] || die "$EXIT_USAGE" 'POSTGRES_PASSWORD is required.'

require_cmd docker
require_cmd timeout
require_cmd curl

cd "$ROOT_DIR"

compose_cmd=(docker compose --ansi never)
if [[ -n "$PROJECT_NAME" ]]; then
  compose_cmd+=(--project-name "$PROJECT_NAME")
fi
compose_cmd+=(--env-file "$ENV_FILE" -f "$COMPOSE_FILE")

if [[ -n "$COMPOSE_PROFILES_RAW" ]]; then
  read -r -a compose_profiles <<< "$COMPOSE_PROFILES_RAW"
  for profile in "${compose_profiles[@]}"; do
    compose_cmd+=(--profile "$profile")
  done
fi

compose_services=()
if [[ -n "$COMPOSE_SERVICES_RAW" ]]; then
  read -r -a compose_services <<< "$COMPOSE_SERVICES_RAW"
fi

api_log_service="${API_SERVICE_NAME:-api-control-plane}"
if [[ -z "${API_SERVICE_NAME:-}" ]]; then
  for service in "${compose_services[@]}"; do
    if [[ "$service" == api-control-plane* ]]; then
      api_log_service="$service"
      break
    fi
  done
fi

log "starting first-time build+run using $COMPOSE_FILE"
run_with_timeout "$COMPOSE_TIMEOUT" "${compose_cmd[@]}" up -d --build --remove-orphans "${compose_services[@]}"
if ! poll_http_health "$API_HEALTH_URL" "$HEALTH_RETRIES" "$HEALTH_SLEEP_SECONDS" "$HEALTH_REQUEST_TIMEOUT"; then
  log 'health check failed; collecting compose diagnostics.'
  run_with_timeout 30s "${compose_cmd[@]}" ps || true
  run_with_timeout 30s "${compose_cmd[@]}" logs --tail=200 "$api_log_service" postgres redis || true
  die "$EXIT_HEALTH" "health check failed: $API_HEALTH_URL"
fi
print_tailscale_info
log 'first-time build+run complete.'
