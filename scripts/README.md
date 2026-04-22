# scripts

Automation entry points.

## Quality checks

- `scripts/lint-all.sh`: Python lint/format/type checks.
- `scripts/test-all.sh`: Python test suite entry point.

## Ops workflows

Shared helpers:

- `scripts/ops/lib.sh`: strict mode, timeout wrappers, health polling, and standardized error exits.

Entry points:

- `scripts/ops/first-time-build-run.sh`: first deployment (`docker compose up -d --build` + health polling).
- `scripts/ops/subsequent-run.sh`: idempotent routine start (`docker compose up -d` + health polling).
- `scripts/ops/update-build-run.sh`: pull updates, rebuild, and restart (`docker compose pull` + `up -d --build`).

Usage examples:

```bash
GB_API_AUTH_TOKEN='replace-with-long-random-token' \
POSTGRES_PASSWORD='replace-with-strong-password' \
./scripts/ops/first-time-build-run.sh

COMPOSE_FILE='infra/compose/docker-compose.prod.yml' \
./scripts/ops/subsequent-run.sh

PULL_TIMEOUT='20m' COMPOSE_TIMEOUT='25m' \
./scripts/ops/update-build-run.sh
```

Notes:

- Scripts are non-interactive (`--ansi never`) and include explicit timeouts for long-running commands.
- Health polling targets `API_HEALTH_URL` (default `http://127.0.0.1:8000/healthz`) with bounded retries.
- Scripts print concise status and a brief Tailscale summary (if `tailscale` is installed).

Exit codes:

- `0`: success.
- `64`: usage error (for example, required env vars missing).
- `69`: dependency missing (for example, `docker`, `curl`, `timeout`).
- `70`: health check did not succeed within retry budget.
- `124`: command timed out.
- Any other non-zero code: underlying command/runtime failure.

## Release skeleton

- `scripts/release/gen-version-metadata.sh <version> [channel] [output]`
- `scripts/release/build-desktop-artifacts.sh <version> [output-dir]`
- `scripts/release/build-push-server-images.sh <version> [registry]`

These release scripts are intentionally cloud-agnostic and do not perform cloud deployment.
