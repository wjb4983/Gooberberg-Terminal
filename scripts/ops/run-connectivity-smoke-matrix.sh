#!/usr/bin/env bash
set -euo pipefail

LOCALHOST_BASE_URL="${LOCALHOST_BASE_URL:-http://127.0.0.1:8000}"
TAILSCALE_BASE_URL="${TAILSCALE_BASE_URL:-}"
REVERSE_PROXY_BASE_URL="${REVERSE_PROXY_BASE_URL:-}"

run_topology() {
  local topology="$1"
  local base_url="$2"
  if [[ -z "$base_url" ]]; then
    echo "WARN skipping topology=${topology} (base URL not configured)"
    return 0
  fi
  timeout 60s scripts/ops/connectivity-synthetic-check.sh "$topology" "$base_url"
}

run_topology localhost "$LOCALHOST_BASE_URL"
run_topology tailscale "$TAILSCALE_BASE_URL"
run_topology reverse-proxy "$REVERSE_PROXY_BASE_URL"
