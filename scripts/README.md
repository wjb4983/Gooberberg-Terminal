# scripts

Automation entry points.

## Quality checks

- `scripts/lint-all.sh`: Python lint/format/type checks.
- `scripts/test-all.sh`: Python test suite entry point.
- `scripts/test-connectivity-layered.sh`: Layered connectivity verification (unit/integration/e2e contract smoke).

## Ops workflows

Shared helpers:

- `scripts/ops/lib.sh`: strict mode, timeout wrappers, health polling, and standardized error exits.

Entry points:

- `scripts/ops/first-time-build-run.sh`: first deployment (`docker compose up -d --build` + health polling).
- `scripts/ops/subsequent-run.sh`: idempotent routine start (`docker compose up -d` + health polling).
- `scripts/ops/update-build-run.sh`: pull updates, rebuild, and restart (`docker compose pull` + `up -d --build`).
- `scripts/ops/connectivity-synthetic-check.sh`: single-topology synthetic health/auth/backend-down/queue/ws checks.
- `scripts/ops/run-connectivity-smoke-matrix.sh`: run connectivity synthetic smoke across localhost, tailscale, and reverse-proxy base URLs.

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
- Scripts automatically load `config/env/.env` by default (`ENV_FILE` override) and pass it to Docker Compose via `--env-file`.
- Health polling targets `API_HEALTH_URL` (default derived from `API_BIND_IP`/`API_BIND_PORT`, falling back to `http://127.0.0.1:8000/healthz`) with bounded retries.
- Scripts print concise status and a brief Tailscale summary (if `tailscale` is installed).

## Quick order of operations (beginner-friendly)

Use this exact sequence on the **server**.

### A) First-time setup (new machine)

1. Set required secrets and run:

   ```bash
   GB_API_AUTH_TOKEN='replace-with-long-random-token' \
   POSTGRES_PASSWORD='replace-with-strong-password' \
   timeout 30m ./scripts/ops/first-time-build-run.sh
   ```

2. On the server, map HTTPS tailnet traffic to the API:

   ```bash
   timeout 20s tailscale serve --https=443 http://127.0.0.1:8000
   timeout 20s tailscale status --self
   ```
   If you see `listener already exists for port 443`, run:
   ```bash
   timeout 20s tailscale serve status
   ```
   and confirm the existing mapping points to `http://127.0.0.1:8000`.

3. On your **other machine** (same tailnet), open:
   - `https://<server>.<tailnet>.ts.net/healthz`
   - `https://<server>.<tailnet>.ts.net/api/v1/health` (not `/api/v1/healthz`)

4. For authenticated API calls from the other machine:

   ```bash
   timeout 20s curl -kfsS "https://<server>.<tailnet>.ts.net/api/v1/models/deployments" \
     -H "Authorization: Bearer <GB_API_AUTH_TOKEN>"
   ```

### B) After `git pull` (repo updates)

1. Pull latest code on server:

   ```bash
   timeout 60s git pull --ff-only
   ```

2. Rebuild/restart services:

   ```bash
   timeout 30m ./scripts/ops/update-build-run.sh
   ```

3. Re-check from the other machine:
   - `https://<server>.<tailnet>.ts.net/healthz`
   - `https://<server>.<tailnet>.ts.net/api/v1/health` (not `/api/v1/healthz`)

### C) Routine restart (no code updates)

1. Start existing stack:

   ```bash
   timeout 20m ./scripts/ops/subsequent-run.sh
   ```

2. Re-check from the other machine:
   - `https://<server>.<tailnet>.ts.net/healthz`
   - `https://<server>.<tailnet>.ts.net/api/v1/health` (not `/api/v1/healthz`)

If a script reports health check failure, inspect containers immediately:

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=200 api-control-plane postgres redis
```

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

## Scaffolding

- `scripts/gen-model-adapter.py <model_id>`: generate a provider adapter class, validation stub, service-data unit test template, and docs entry under `docs/model-adapters/`.
