# scripts

Automation entry points.

## Quality checks

- `scripts/lint-all.sh`: Python lint/format/type checks.
- `scripts/test-all.sh`: Python test suite entry point.
- `scripts/test-connectivity-layered.sh`: Layered connectivity verification (unit/integration/e2e contract smoke).
- `scripts/dev/check-local-fullstack.sh`: finite local full-stack smoke check for the API health endpoints and frontend dev port after startup.


## Local development quick start

Run these tasks from the repository root in the recommended order:

1. Start backend dependencies and the API control plane:

   ```bash
   timeout 120s docker compose -f infra/compose/docker-compose.dev.yml up --build api-control-plane postgres redis
   ```

2. Start the frontend in a second terminal:

   ```bash
   timeout 120s pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
   ```

3. Open the VS Code forwarded frontend URL for port `1420`.

4. Run the smoke check from another terminal:

   ```bash
   timeout 60s scripts/dev/check-local-fullstack.sh
   ```

5. Stop the local stack when finished:

   ```bash
   timeout 60s docker compose -f infra/compose/docker-compose.dev.yml down --remove-orphans
   ```

## Ops workflows

Shared helpers:

- `scripts/ops/lib.sh`: strict mode, timeout wrappers, health polling, and standardized error exits.

Entry points:

- `scripts/ops/first-time-build-run.sh`: first deployment (`docker compose up -d --build` + health polling).
- `scripts/ops/subsequent-run.sh`: idempotent routine start (`docker compose up -d` + health polling).
- `scripts/ops/update-build-run.sh`: pull updates, rebuild, and restart (`docker compose pull` + `up -d --build`).
- `scripts/ops/connectivity-synthetic-check.sh`: single local synthetic health/auth/backend-down/queue/ws check.

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
- Scripts use the compose file's project name by default; set `COMPOSE_PROJECT_NAME` only when you intentionally need a non-default project namespace.
- `COMPOSE_PROFILES` accepts a space-delimited list of compose profiles, and `COMPOSE_SERVICES` accepts a space-delimited list of services to target.
- Health polling targets `API_HEALTH_URL` (default derived from `API_BIND_IP`/`API_BIND_PORT`, falling back to `http://127.0.0.1:8000/healthz`) with bounded retries.

## Quick order of operations (beginner-friendly)

Use this exact sequence on the local development machine or dev container.

### A) First-time setup

1. Set required secrets and run:

   ```bash
   GB_API_AUTH_TOKEN='replace-with-long-random-token' \
   POSTGRES_PASSWORD='replace-with-strong-password' \
   timeout 30m ./scripts/ops/first-time-build-run.sh
   ```

2. Verify local backend health:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

3. Start or verify the frontend on `127.0.0.1:1420`, then open it through your local browser or VS Code forwarded port.

### B) After `git pull` (repo updates)

1. Pull latest code:

   ```bash
   timeout 60s git pull --ff-only
   ```

2. Rebuild/restart services:

   ```bash
   timeout 30m ./scripts/ops/update-build-run.sh
   ```

3. Re-check local health:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

### C) Routine restart (no code updates)

1. Start existing stack:

   ```bash
   timeout 20m ./scripts/ops/subsequent-run.sh
   ```

2. Re-check local health:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

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

1. **Verify health endpoints first**:

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
   - Desktop popups now include optional correlation metadata like `request_id=<uuid>` and `error_code=<code>`.
   - Search API logs by request id to reconstruct the exact request path/method/auth result and dependency failures.
   - Example:

   ```bash
   timeout 20s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=500 api-control-plane | rg "request_id=<paste-request-id>|\"request_id\":\"<paste-request-id>\""
   ```

See `docs/runbooks/local-server-browser.md` for the browser and VS Code port-forward workflow.
