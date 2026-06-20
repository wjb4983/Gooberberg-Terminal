# Local development runbook

This runbook is designed so a new engineer can clone, run, validate, and troubleshoot the control plane locally.

## Supported local server topology

The supported development topology is a single local/VS Code workspace:

- Backend dependencies and the API run from Docker Compose and publish the API on `127.0.0.1:8000`.
- The frontend dev server listens on port `1420` for VS Code port forwarding/browser access.
- The frontend talks to the API at `http://127.0.0.1:8000`.
- External access patterns are intentionally out of scope for primary local development docs.

## Quick start: local full stack

Run these tasks from the repository root in order. Each task is independently verifiable; stop and fix the first failed step before continuing.

1. Start the backend dependencies/API:

   ```bash
   timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
   ```

2. Start the frontend dev server:

   ```bash
   timeout 8h pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
   ```

3. Open the VS Code forwarded/browser URL for port `1420`.

4. Confirm the frontend API base URL is `http://127.0.0.1:8000`.

   If the app Settings page shows a different value, set it to `http://127.0.0.1:8000` to avoid `localhost` IPv4/IPv6 ambiguity.

5. Run finite smoke checks from a second terminal:

   ```bash
   timeout 60s ./scripts/dev/check-local-fullstack.sh
   ```

6. After closing the frontend, stop the local backend containers:

   ```bash
   timeout 120s pnpm dev:local:down
   ```

   This stops the backend/API Compose containers and removes orphaned containers, but it does not remove persistent Docker volumes. Only remove persistent local data when you explicitly intend to reset it with a destructive cleanup command such as:

   ```bash
   timeout 60s docker compose -f infra/compose/docker-compose.dev.yml down --remove-orphans --volumes
   ```

## 1) Prerequisites

- Node.js + pnpm (workspace uses pinned package manager in root `package.json`).
- Python toolchain for backend checks (`ruff`, `black`, `mypy`, `pytest`).
- Docker Engine + Compose plugin.
- Git.

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

The supported quick start uses Docker Compose. For API-only development without Docker, run from the repository root:

```bash
cd apps/api-control-plane && timeout 2m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> Tip: for longer interactive sessions, run the same command in your own terminal with a bounded `timeout` value that matches your work session.

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

## 7) Frontend local mode

Use the same order as the quick start:

1. Start backend dependencies/API on `127.0.0.1:8000`.
2. Start the frontend dev server on port `1420`.
3. Open the VS Code forwarded/browser URL for port `1420`.
4. Confirm Settings uses `http://127.0.0.1:8000` as the frontend API base URL.
5. Run finite smoke checks with `timeout 60s ./scripts/dev/check-local-fullstack.sh`.

Manual API checks:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
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

## 10) Local release dry-run (server images only)

```bash
VERSION=0.1.0

timeout 2m scripts/release/gen-version-metadata.sh "$VERSION"
timeout 90m scripts/release/build-push-server-images.sh "$VERSION"
```

By default, the server image script builds but does not push unless `PUSH_IMAGES=true`.
