#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.dev.yml}"
COMPOSE_TIMEOUT="${COMPOSE_TIMEOUT:-20m}"
HEALTH_RETRIES="${HEALTH_RETRIES:-60}"
HEALTH_SLEEP_SECONDS="${HEALTH_SLEEP_SECONDS:-2}"
HEALTH_REQUEST_TIMEOUT="${HEALTH_REQUEST_TIMEOUT:-3}"
BACKEND_HEALTH_URL="http://127.0.0.1:8000/healthz"
VITE_PORT="${VITE_PORT:-1420}"
VITE_HOST="${VITE_HOST:-${LOCAL_FULLSTACK_VITE_HOST:-127.0.0.1}}"
FRONTEND_URL="http://127.0.0.1:${VITE_PORT}"

log() {
  printf '[local-fullstack] %s\n' "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'error: required command not found: %s\n' "$1" >&2
    exit 69
  fi
}

validate_vite_host() {
  case "$VITE_HOST" in
    127.0.0.1|0.0.0.0) ;;
    *)
      printf 'error: VITE_HOST must be either 127.0.0.1 or 0.0.0.0, got: %s\n' "$VITE_HOST" >&2
      exit 64
      ;;
  esac
}

compose() {
  timeout "$COMPOSE_TIMEOUT" docker compose -f "$COMPOSE_FILE" "$@"
}

compose_up_backend() {
  compose up -d --build postgres api-control-plane
}

poll_http_health() {
  local url="$1"
  local attempt

  for ((attempt = 1; attempt <= HEALTH_RETRIES; attempt += 1)); do
    if timeout "$HEALTH_REQUEST_TIMEOUT" curl --fail --silent --show-error --max-time "$HEALTH_REQUEST_TIMEOUT" "$url" >/dev/null; then
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
validate_vite_host

cd "$ROOT_DIR"

log "starting minimal backend stack with Docker Compose"
compose_up_backend

log "waiting for backend health: $BACKEND_HEALTH_URL"
if ! poll_http_health "$BACKEND_HEALTH_URL"; then
  log "backend health check failed; collecting diagnostics"
  timeout 30s docker compose -f "$COMPOSE_FILE" ps || true
  timeout 30s docker compose -f "$COMPOSE_FILE" logs --tail=200 api-control-plane postgres || true
  printf 'error: backend health check failed: %s\n' "$BACKEND_HEALTH_URL" >&2
  exit 70
fi

log "local URLs:"
log "  frontend:       $FRONTEND_URL"
log "  backend health: $BACKEND_HEALTH_URL"
log "VS Code browser guidance: forward port ${VITE_PORT}, then open the forwarded frontend URL."
log "Use VITE_HOST=0.0.0.0 when VS Code port forwarding cannot reach a 127.0.0.1-bound Vite server; otherwise keep VITE_HOST=127.0.0.1."

pnpm --filter @gb/desktop-tauri dev -- --host "$VITE_HOST" --port "$VITE_PORT" --strictPort
