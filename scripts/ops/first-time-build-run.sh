#!/usr/bin/env bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ops/lib.sh
source "$ROOT_DIR/scripts/ops/lib.sh"

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.prod.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-gooberberg}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/healthz}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-20m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-30}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"

[[ -n "${GB_API_AUTH_TOKEN:-}" ]] || die "$EXIT_USAGE" 'GB_API_AUTH_TOKEN is required.'
[[ -n "${POSTGRES_PASSWORD:-}" ]] || die "$EXIT_USAGE" 'POSTGRES_PASSWORD is required.'

require_cmd docker
require_cmd timeout
require_cmd curl

cd "$ROOT_DIR"

log "starting first-time build+run using $COMPOSE_FILE"
run_with_timeout "$COMPOSE_TIMEOUT" docker compose --ansi never --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build --remove-orphans
poll_http_health "$API_HEALTH_URL" "$HEALTH_RETRIES" "$HEALTH_SLEEP_SECONDS" "$HEALTH_REQUEST_TIMEOUT"
print_tailscale_info
log 'first-time build+run complete.'
