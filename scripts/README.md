# scripts

Automation entry points.

## Quality checks

- `scripts/lint-all.sh`: Python lint/format/type checks.
- `scripts/test-all.sh`: Python test suite entry point.
- `scripts/test-connectivity-layered.sh`: Layered connectivity verification (unit/integration/e2e contract smoke).
- `scripts/dev/check-local-fullstack.sh`: finite local full-stack smoke check for the API health endpoints and frontend dev port after startup.

## Supported local quick start

Use this exact sequence from the repository root.

1. Start backend dependencies/API:

   ```bash
   timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
   ```

2. Start the frontend dev server:

   ```bash
   timeout 8h pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
   ```

3. Open the VS Code forwarded/browser URL for port `1420`.

4. Confirm the frontend API base URL is `http://127.0.0.1:8000`.

5. Run finite smoke checks from a second terminal:

   ```bash
   timeout 60s ./scripts/dev/check-local-fullstack.sh
   ```

6. Stop the backend stack when finished:

   ```bash
   timeout 120s pnpm dev:local:down
   ```

## Ops workflows

Shared helpers:

- `scripts/ops/lib.sh`: strict mode, timeout wrappers, health polling, and standardized error exits.

Entry points:

- `scripts/ops/first-time-build-run.sh`: first local/server startup (`docker compose up -d --build` + health polling).
- `scripts/ops/subsequent-run.sh`: idempotent routine start (`docker compose up -d` + health polling).
- `scripts/ops/update-build-run.sh`: pull updates, rebuild, and restart (`docker compose pull` + `up -d --build`).
- `scripts/ops/connectivity-synthetic-check.sh`: single-topology synthetic health/auth/backend-down/queue/ws checks.
- `scripts/ops/run-connectivity-smoke-matrix.sh`: broader connectivity smoke runner for configured local base URLs.

Usage examples:

```bash
GB_API_AUTH_TOKEN='replace-with-long-random-token' \
POSTGRES_PASSWORD='replace-with-strong-password' \
timeout 30m ./scripts/ops/first-time-build-run.sh

timeout 20m ./scripts/ops/subsequent-run.sh

PULL_TIMEOUT='20m' COMPOSE_TIMEOUT='25m' \
timeout 30m ./scripts/ops/update-build-run.sh
```

Notes:

- Scripts are non-interactive (`--ansi never`) and include explicit timeouts for long-running commands.
- Scripts automatically load `config/env/.env` by default (`ENV_FILE` override) and pass it to Docker Compose via `--env-file`.
- Scripts use the compose file's project name by default; set `COMPOSE_PROJECT_NAME` only when you intentionally need a non-default project namespace.
- Health polling targets `API_HEALTH_URL` (default derived from `API_BIND_IP`/`API_BIND_PORT`, falling back to `http://127.0.0.1:8000/healthz`) with bounded retries.

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
- `scripts/release/build-push-server-images.sh <version> [registry]`

These release scripts are intentionally cloud-agnostic and do not perform cloud deployment.

## Scaffolding

- `scripts/gen-model-adapter.py <model_id>`: generate a provider adapter class, validation stub, service-data unit test template, and docs entry under `docs/model-adapters/`.

## Local deployed agent debug flow

Use this sequence when a local deployed agent reports an API popup/error.

1. **Verify local health endpoints first**:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

2. **Run bounded connectivity synthetic checks**:

   ```bash
   timeout 8m ./scripts/ops/connectivity-synthetic-check.sh
   ```

3. **Fetch relevant service logs with timeout** (focus API + backing services):

   ```bash
   timeout 45s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=300 api-control-plane
   timeout 45s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=200 redis postgres
   ```

4. **Map client error to server request id**:
   - Desktop popups can include optional correlation metadata like `request_id=<uuid>` and `error_code=<code>`.
   - Search API logs by request id to reconstruct the exact request path/method/auth result and dependency failures.
   - Example:

   ```bash
   timeout 20s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=500 api-control-plane | rg "request_id=<paste-request-id>|\"request_id\":\"<paste-request-id>\""
   ```
