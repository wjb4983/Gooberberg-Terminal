# Local development runbook

This runbook documents a repeatable local workflow for linting, testing, and validating release artifacts without deploying anything to cloud providers.

## Prerequisites

- Node.js + pnpm (workspace root `packageManager` is pinned in `package.json`).
- Python tooling (`ruff`, `black`, `mypy`, `pytest`) for backend checks.
- Docker engine for local image builds.
- Git with tags available for release/version automation.

## Day-to-day workflow

1. Install dependencies.
2. Run lint checks.
3. Run tests.
4. Build relevant packages/apps.
5. Optionally generate release artifacts locally.

### Commands

```bash
timeout 10m pnpm install --frozen-lockfile
timeout 5m scripts/lint-all.sh
timeout 10m scripts/test-all.sh
timeout 10m pnpm build
```

## Local release dry-run (no cloud deployment)

Choose a semantic version and run release scripts locally:

```bash
VERSION=0.1.0

timeout 2m scripts/release/gen-version-metadata.sh "$VERSION"
timeout 30m scripts/release/build-desktop-artifacts.sh "$VERSION"
timeout 90m scripts/release/build-push-server-images.sh "$VERSION"
```

By default, `build-push-server-images.sh` builds Docker images and **does not push**. To push to a container registry, set `PUSH_IMAGES=true` explicitly.

## Scope guardrails

- This repository currently supports **build and packaging preparation only**.
- No script in the baseline release flow deploys to AWS, GCP, Azure, or any cloud provider.
