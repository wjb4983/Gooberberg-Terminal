#!/usr/bin/env bash
set -euo pipefail

LOCALHOST_BASE_URL="${LOCALHOST_BASE_URL:-http://127.0.0.1:8000}"
TAILSCALE_BASE_URL="${TAILSCALE_BASE_URL:-}"
REVERSE_PROXY_BASE_URL="${REVERSE_PROXY_BASE_URL:-}"
REMOTE_BASE_URLS="${REMOTE_BASE_URLS:-}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-90}"

failures=0

run_topology() {
  local topology="$1"
  local base_url="$2"
  if [[ -z "$base_url" ]]; then
    echo "WARN skipping topology=${topology} (base URL not configured)"
    return 0
  fi

  echo "RUN topology=${topology} base_url=${base_url}"
  if timeout "${SMOKE_TIMEOUT_SECONDS}s" scripts/ops/connectivity-synthetic-check.sh "$topology" "$base_url"; then
    echo "PASS topology=${topology}"
  else
    failures=$((failures + 1))
    echo "FAIL topology=${topology}" >&2
  fi
}

run_topology localhost "$LOCALHOST_BASE_URL"
run_topology tailscale "$TAILSCALE_BASE_URL"
run_topology reverse-proxy "$REVERSE_PROXY_BASE_URL"

if [[ -n "$REMOTE_BASE_URLS" ]]; then
  index=1
  for remote_url in $REMOTE_BASE_URLS; do
    run_topology "remote-${index}" "$remote_url"
    index=$((index + 1))
  done
fi

if [[ "$failures" -gt 0 ]]; then
  echo "Connectivity smoke matrix failed topologies=${failures}" >&2
  exit 1
fi

echo "Connectivity smoke matrix passed"
