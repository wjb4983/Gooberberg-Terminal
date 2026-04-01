# scripts

Automation entry points.

## Quality checks

- `scripts/lint-all.sh`: Python lint/format/type checks.
- `scripts/test-all.sh`: Python test suite entry point.

## Release skeleton

- `scripts/release/gen-version-metadata.sh <version> [channel] [output]`
- `scripts/release/build-desktop-artifacts.sh <version> [output-dir]`
- `scripts/release/build-push-server-images.sh <version> [registry]`

These release scripts are intentionally cloud-agnostic and do not perform cloud deployment.
