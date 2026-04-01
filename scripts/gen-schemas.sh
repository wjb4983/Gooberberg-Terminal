#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_FILE="$ROOT_DIR/libs/ts/@gb/schemas/src/generated/openapi.ts"
OPENAPI_URL="${GB_OPENAPI_URL:-http://localhost:8000/openapi.json}"

mkdir -p "$(dirname "$OUTPUT_FILE")"

echo "Generating TypeScript schema types from: $OPENAPI_URL"
pnpm --silent dlx openapi-typescript "$OPENAPI_URL" --output "$OUTPUT_FILE"

echo "Wrote generated schema file: $OUTPUT_FILE"
echo "Note: Keep libs/ts/@gb/schemas/src/index.ts as hand-curated stable contract surface."
