#!/usr/bin/env bash
# Shared helpers for ops automation scripts.

set -euo pipefail

readonly EXIT_USAGE=64
readonly EXIT_DEPENDENCY=69
readonly EXIT_TIMEOUT=124
readonly EXIT_HEALTH=70
readonly EXIT_RUNTIME=1

log() {
  printf '[ops] %s\n' "$*"
}

err() {
  printf '[ops] ERROR: %s\n' "$*" >&2
}

die() {
  local code="${1:-$EXIT_RUNTIME}"
  shift || true
  err "$*"
  exit "$code"
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || die "$EXIT_DEPENDENCY" "missing required command: $cmd"
}

run_with_timeout() {
  local timeout_value="$1"
  shift

  local status=0
  timeout "$timeout_value" "$@" || status=$?

  if [[ "$status" -eq 0 ]]; then
    return 0
  fi

  if [[ "$status" -eq 124 ]]; then
    die "$EXIT_TIMEOUT" "timed out after $timeout_value: $*"
  fi

  die "$status" "command failed (exit $status): $*"
}

poll_until_success() {
  local max_retries="$1"
  local sleep_seconds="$2"
  local check_timeout="$3"
  shift 3

  local attempt
  for ((attempt = 1; attempt <= max_retries; attempt++)); do
    if timeout "$check_timeout" "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_seconds"
  done

  return 1
}

poll_http_health() {
  local url="$1"
  local max_retries="$2"
  local sleep_seconds="$3"
  local request_timeout="$4"

  if poll_until_success "$max_retries" "$sleep_seconds" "$request_timeout" curl -fsS --max-time "$request_timeout" "$url"; then
    log "health check ok: $url"
    return 0
  fi

  err "health check failed after ${max_retries} attempts: $url"
  return 1
}
