# Local development runbook

This runbook is designed so a new engineer can clone, run, validate, and troubleshoot the control plane locally.

## Quick start: local full stack

Run these tasks from the repository root in order. Each task is independently verifiable; stop and fix the first failed step before continuing.

1. Install dependencies:

   ```bash
   timeout 10m pnpm install --frozen-lockfile
   ```

2. Start the backend/API stack:

   ```bash
   timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
   ```

3. Verify the backend health endpoints:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

4. Start the frontend dev server:

   ```bash
   pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
   ```

5. Run the finite local full-stack smoke script from a second terminal. It checks the API endpoints, queue health endpoint, and frontend port with bounded timeouts, and fails fast with clear messages if either service is unavailable:

   ```bash
   timeout 60s ./scripts/dev/check-local-fullstack.sh
   ```

6. Open the VS Code forwarded/browser URL for port `1420`.

   The local full-stack script keeps the queue/worker status fresh by posting a local heartbeat while the frontend process is running. If your browser has an older Settings value, set the API base URL to `http://127.0.0.1:8000` to avoid IPv6 `localhost` resolution issues in the dev proxy.

7. After closing the frontend, stop the local backend containers:

   ```bash
   pnpm dev:local:down
   ```

   This stops the backend/API Compose containers and removes orphaned containers, but it does not remove persistent Docker volumes. Only remove persistent local data when you explicitly intend to reset it with a destructive cleanup command such as:

   ```bash
   timeout 60s docker compose -f infra/compose/docker-compose.dev.yml down --remove-orphans --volumes
   ```

## 1) Prerequisites

- Node.js + pnpm (workspace uses pinned package manager in root `package.json`).
- Python toolchain for backend checks (`ruff`, `black`, `mypy`, `pytest`).
- Docker Engine + Compose plugin.
- Git (tags required for release dry-runs).

## 2) Repository bootstrap

```bash
timeout 10m pnpm install --frozen-lockfile
```

## 3) Fast path mental model (local)

Use this to understand request flow while developing:

1. REST call hits FastAPI control plane.
2. Request is auth-validated and handled by router.
3. Lightweight state changes occur in memory (+ Redis repository if configured).
4. WS event is published for subscribed clients.
5. Immediate JSON response returns to caller.

Slow path work (workers, heavy compute, batch artifacts) is out-of-band and represented by references (`result_ref`/`artifact_ref`) in fast-path responses.

## 4) Core quality gates

```bash
timeout 5m scripts/lint-all.sh
timeout 10m scripts/test-all.sh
timeout 10m pnpm build
```

## 5) Run API control plane locally

From repository root:

```bash
cd apps/api-control-plane
timeout 2m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> Tip: for longer sessions, use terminal multiplexers or a script wrapper that restarts uvicorn; keep non-interactive commands timeout-bounded in automation.

## 6) Local API smoke checks

Set an auth token if `GB_API_AUTH_TOKEN` is configured:

```bash
export TOKEN="<your-token>"
```

Health:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

Create and fetch job:

```bash
timeout 20s curl -fsS -X POST http://127.0.0.1:8000/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"job_type":"backfill","payload":{"symbol":"AAPL"}}'

# then fetch with returned id
# timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/jobs/<job_id> -H "Authorization: Bearer $TOKEN"
```

## 7) Full-stack local mode on a remote server

Use this order when running the full stack from a remote development host, such as VS Code Remote SSH or a dev container:

1. Start the API bound only to the remote server loopback interface at `127.0.0.1:8000`.
2. Start Vite/frontend on `0.0.0.0:1420` so the VS Code browser or port forwarding can reach it.
3. Open the app through the VS Code forwarded browser from the same remote environment and configure the frontend API base URL as `http://localhost:8000`.

After startup, run these manual smoke checks from the remote environment before opening the app:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

Then open the VS Code forwarded frontend URL for port `1420`. For a finite scripted check of the API endpoints and frontend port, run this from a second terminal:

```bash
timeout 60s ./scripts/dev/check-local-fullstack.sh
```

## 8) WebSocket smoke checks

Use a WS CLI/client to:

1. Connect `ws://127.0.0.1:8000/ws`.
2. Send: `{"action":"subscribe","topics":["jobs","logs"]}`.
3. Trigger a job creation through HTTP.
4. Confirm topic envelopes with `event_id`, `seq`, `topic`, `timestamp`, `payload`, `version`.

## 9) Troubleshooting (local)

### API issues

- **401 Unauthorized**
  - Verify `Authorization: Bearer <token>` matches `GB_API_AUTH_TOKEN`.
  - Health paths are exempt; use `/api/v1/health` to confirm service liveness.
- **404 on expected route**
  - Confirm prefix is `/api/v1` (or your configured `GB_API_PREFIX`).
- **500s at startup**
  - Check uvicorn tracebacks and environment variables.

### WebSocket issues

- **No topic events received**
  - Ensure you subscribed to valid topics (`jobs`, `alerts`, `logs`, `portfolio`, `risk`, `strategy`, `models`).
- **Frequent disconnects**
  - Verify heartbeat handling (`ping`/`pong`) in client.
- **Malformed message errors**
  - Send valid JSON messages with supported `action`.

### Redis issues

- **Redis unavailable locally**
  - API should continue with in-memory fallback; verify logs for `redis ping failed; api continues with in-memory fallback`.
- **Job state not surviving restart**
  - Expected without Redis persistence.
- **Portfolio snapshots not updating**
  - Ensure Redis pub/sub message is JSON string on `portfolio.snapshot` channel.

### Postgres issues

- Health endpoint currently reports placeholder connectivity detail.
- Verify DSN configuration separately in env and service logs.
- In compose environments, confirm `postgres` container health and credentials.

## 10) Local release dry-run (no cloud deployment)

```bash
VERSION=0.1.0

timeout 2m scripts/release/gen-version-metadata.sh "$VERSION"
timeout 30m scripts/release/build-desktop-artifacts.sh "$VERSION"
timeout 90m scripts/release/build-push-server-images.sh "$VERSION"
```

By default, server image script builds but does not push unless `PUSH_IMAGES=true`.
