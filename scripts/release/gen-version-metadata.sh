#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-}"
CHANNEL="${2:-stable}"
OUTPUT_PATH="${3:-dist/version-metadata.json}"

if [[ -z "$VERSION" ]]; then
  if git describe --tags --abbrev=0 >/dev/null 2>&1; then
    VERSION="$(git describe --tags --abbrev=0 | sed 's/^v//')"
  else
    echo "Error: no version argument provided and no git tags found." >&2
    echo "Usage: $0 <semver-version> [channel] [output-path]" >&2
    exit 1
  fi
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([-+][A-Za-z0-9.-]+)?$ ]]; then
  echo "Error: version '$VERSION' is not valid semver (MAJOR.MINOR.PATCH with optional suffix)." >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT_PATH")"

GIT_SHA="$(git rev-parse --short=12 HEAD)"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
BUILD_TIME_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cat > "$OUTPUT_PATH" <<JSON
{
  "version": "$VERSION",
  "channel": "$CHANNEL",
  "git_sha": "$GIT_SHA",
  "git_branch": "$GIT_BRANCH",
  "built_at_utc": "$BUILD_TIME_UTC"
}
JSON

echo "Wrote version metadata to $OUTPUT_PATH"
