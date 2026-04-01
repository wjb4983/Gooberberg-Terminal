#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-}"
OUTPUT_DIR="${2:-dist/desktop}"

if [[ -z "$VERSION" ]]; then
  echo "Error: version argument is required." >&2
  echo "Usage: $0 <semver-version> [output-dir]" >&2
  exit 1
fi

scripts/release/gen-version-metadata.sh "$VERSION" stable "$OUTPUT_DIR/version-metadata.json"

mkdir -p "$OUTPUT_DIR"

echo "Building desktop web assets (placeholder command)..."
timeout 20m pnpm --filter ./apps/desktop-tauri build

echo "Packaging Tauri desktop bundles (placeholder command)..."
timeout 20m pnpm --filter ./apps/desktop-tauri tauri build || {
  echo "Warning: tauri build command failed or is not configured yet."
  echo "Skeleton script created; wire this command to your real packaging pipeline."
}

echo "Desktop artifact skeleton complete. Expected outputs are under $OUTPUT_DIR."
