# api-control-plane

FastAPI service for Gooberberg operator/control-plane APIs.

## Supported local server topology

The supported local topology keeps the API on loopback and the frontend in the same local/VS Code workspace:

- Docker Compose starts Postgres, Redis, and the API.
- The API publishes on `127.0.0.1:8000`.
- The frontend dev server runs on port `1420`.
- The frontend API base URL must be `http://127.0.0.1:8000`.

## Quick start: backend/API portion

Run this backend sequence from the repository root before starting the frontend:

```bash
# 1) Clean up old compose state
timeout 60s docker compose -f infra/compose/docker-compose.dev.yml down --remove-orphans

# 2) Build and start DB/cache/API
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane

# 3) Confirm API container is running
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml ps api-control-plane

# 4) If not running, inspect API logs immediately
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane

# 5) Local API checks
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

After these pass, start the frontend dev server, open the VS Code forwarded/browser URL for port `1420`, confirm the frontend API base URL is `http://127.0.0.1:8000`, and run `timeout 60s ./scripts/dev/check-local-fullstack.sh` from a second terminal.

If step 3 shows no `api-control-plane` row, step 4 logs are the source of truth.

## What this service exposes

- Root status endpoint: `GET /`
- Liveness endpoint: `GET /healthz` (no auth)
- Versioned API health endpoint: `GET /api/v1/health` (no auth)
- Control-plane routes under `GET/POST /api/v1/*` (bearer auth required when `GB_API_AUTH_TOKEN` is set)

## Local run (without Docker)

From repo root:

```bash
timeout 60s uv pip install -e libs/py/gb_core -e apps/api-control-plane
```

Start the API server for a bounded local session:

```bash
timeout 2h uvicorn app.main:app --host 127.0.0.1 --port 8000
```

For reload behavior during development, keep the command bounded:

```bash
timeout 2h uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Docker run (dev compose)

Build and start dependencies + API:

```bash
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
```

Then confirm the API container is actually running (not exited):

```bash
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml ps api-control-plane
```

Important:

- The dev compose file publishes the API on **`127.0.0.1:8000`**.
- If `curl http://127.0.0.1:8001/...` fails, that is expected unless you explicitly remap ports.

Restart API only after code changes:

```bash
timeout 180s docker compose -f infra/compose/docker-compose.dev.yml up -d --build api-control-plane
```

## Verification checklist

After starting/restarting, run these checks in order.

1) Containers are up:

```bash
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml ps
```

2) Local liveness endpoint responds:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
```

3) Versioned API health responds:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

4) Root status responds:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/
```

5) If something fails, inspect logs:

```bash
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane postgres redis
```

6) If `curl` says **connection refused**, the API container likely crashed during startup. Rebuild and relaunch, then re-check logs:

```bash
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml ps api-control-plane
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane
```

## Domain production rollout flags

All flags are prefixed with `GB_` and are **default-safe** (`false`) to keep production paths disabled until explicitly enabled.

| Domain | Flag | Default | Disabled behavior |
|---|---|---:|---|
| Worker research | `GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED` | `false` | Return/record `degraded` + structured reason and deterministic fallback |
| Portfolio state | `GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED` | `false` | Return/record `degraded` + structured reason and deterministic fallback |
| Graph domain | `GB_GRAPH_PROD_TOPOLOGY_ENABLED` | `false` | Return/record `degraded` + structured reason and deterministic fallback |
| Health checks | `GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED` | `false` | Return/record `degraded` + structured reason and deterministic fallback |

Structured reason contract and deterministic guarantees are documented in `docs/architecture/deterministic-pipelines.md`.
