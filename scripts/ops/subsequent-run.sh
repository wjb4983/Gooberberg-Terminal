#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ops/lib.sh
source "$ROOT_DIR/scripts/ops/lib.sh"

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.prod.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gooberberg}"
API_BIND_IP="${API_BIND_IP:-0.0.0.0}"
API_BIND_PORT="${API_BIND_PORT:-8000}"
API_HEALTH_HOST="${API_BIND_IP}"
if [[ "$API_HEALTH_HOST" == "0.0.0.0" ]]; then
  API_HEALTH_HOST="127.0.0.1"
fi
API_HEALTH_URL="${API_HEALTH_URL:-http://${API_HEALTH_HOST}:${API_BIND_PORT}/healthz}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-10m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-60}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"

require_cmd docker
require_cmd timeout
require_cmd curl

cd "$ROOT_DIR"

log "starting subsequent run using $COMPOSE_FILE"
run_with_timeout "$COMPOSE_TIMEOUT" docker compose --ansi never --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --remove-orphans
poll_http_health "$API_HEALTH_URL" "$HEALTH_RETRIES" "$HEALTH_SLEEP_SECONDS" "$HEALTH_REQUEST_TIMEOUT"
print_tailscale_info
log 'subsequent run complete.'
