#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.dev.yml}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-20m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-60}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"
FRONTEND_URL="http://127.0.0.1:1420"
BACKEND_HEALTH_URL="http://127.0.0.1:8000/healthz"
VERSIONED_HEALTH_URL="http://127.0.0.1:8000/api/v1/health"
QUEUE_HEARTBEAT_URL="http://127.0.0.1:8000/api/v1/health/queue/heartbeat"
HEARTBEAT_INTERVAL_SECONDS="${HEARTBEAT_INTERVAL_SECONDS:-30}"

log() {
  printf '[local-fullstack] %s\n' "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'error: required command not found: %s\n' "$1" >&2
    exit 69
  fi
}

poll_http_health() {
  local url="$1"
  local attempt

  for ((attempt = 1; attempt <= HEALTH_RETRIES; attempt += 1)); do
    if curl --fail --silent --show-error --max-time "$HEALTH_REQUEST_TIMEOUT" "$url" >/dev/null; then
      return 0
    fi

    if ((attempt < HEALTH_RETRIES)); then
      sleep "$HEALTH_SLEEP_SECONDS"
    fi
  done

  return 1
}

require_cmd docker
require_cmd pnpm
require_cmd timeout
require_cmd curl

cd "$ROOT_DIR"

log "starting backend dependencies/API with Docker Compose"
timeout "$COMPOSE_TIMEOUT" docker compose -f "$COMPOSE_FILE" up -d --build postgres redis api-control-plane

log "waiting for backend health: $BACKEND_HEALTH_URL"
if ! poll_http_health "$BACKEND_HEALTH_URL"; then
  log "backend health check failed; collecting diagnostics"
  timeout 30s docker compose -f "$COMPOSE_FILE" ps || true
  timeout 30s docker compose -f "$COMPOSE_FILE" logs --tail=200 api-control-plane postgres redis || true
  printf 'error: backend health check failed: %s\n' "$BACKEND_HEALTH_URL" >&2
  exit 70
fi

log "local development URLs:"
log "  frontend:         $FRONTEND_URL"
log "  backend health:   $BACKEND_HEALTH_URL"
log "  versioned health: $VERSIONED_HEALTH_URL"
log "starting local queue heartbeat for status bar"
(
  while true; do
    curl --fail --silent --show-error --max-time "$HEALTH_REQUEST_TIMEOUT" \
      --request POST "$QUEUE_HEARTBEAT_URL" >/dev/null || true
    sleep "$HEARTBEAT_INTERVAL_SECONDS"
  done
) &
heartbeat_pid=$!

cleanup() {
  kill "$heartbeat_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

log "starting frontend dev server"

pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
