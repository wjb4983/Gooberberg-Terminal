#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:1420}"
REQUEST_TIMEOUT_SECONDS="${REQUEST_TIMEOUT_SECONDS:-5}"

log() {
  printf '[check-local-fullstack] %s\n' "$*"
}

fail() {
  printf '[check-local-fullstack] error: %s\n' "$*" >&2
  exit 70
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[check-local-fullstack] error: required command not found: %s\n' "$1" >&2
    exit 69
  fi
}

check_http() {
  local label="$1"
  local url="$2"

  log "checking ${label}: ${url}"
  if ! timeout 20s curl -fsS --max-time "$REQUEST_TIMEOUT_SECONDS" "$url" >/dev/null; then
    fail "${label} is unavailable at ${url}. Start the local full stack first and confirm the expected port is forwarded/listening."
  fi
}

require_cmd timeout
require_cmd curl

check_http "API liveness endpoint" "${API_BASE_URL}/healthz"
check_http "API versioned health endpoint" "${API_BASE_URL}/api/v1/health"
check_http "API queue health endpoint" "${API_BASE_URL}/api/v1/health/queue"
check_http "frontend dev server" "${FRONTEND_URL}"

log "all finite local full-stack smoke checks passed"
log "manual browser check: open the VS Code forwarded frontend URL for port 1420"
