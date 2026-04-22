#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ops/lib.sh
source "$ROOT_DIR/scripts/ops/lib.sh"

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.prod.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gooberberg}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/healthz}"
PULL_TIMEOUT="${PULL_TIMEOUT:-15m}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-20m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"

require_cmd docker
require_cmd timeout
require_cmd curl

cd "$ROOT_DIR"

log "updating images and rebuilding stack using $COMPOSE_FILE"
run_with_timeout "$PULL_TIMEOUT" docker compose --ansi never --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" pull --ignore-pull-failures
run_with_timeout "$COMPOSE_TIMEOUT" docker compose --ansi never --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build --remove-orphans
poll_http_health "$API_HEALTH_URL" "$HEALTH_RETRIES" "$HEALTH_SLEEP_SECONDS" "$HEALTH_REQUEST_TIMEOUT"
print_tailscale_info
log 'update build+run complete.'
