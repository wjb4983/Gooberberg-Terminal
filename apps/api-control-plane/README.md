# api-control-plane

FastAPI service for Gooberberg operator/control-plane APIs.

## Copy/paste: bring server online + verify + Tailscale

Run this exact sequence from repo root:

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

# 6) Expose over Tailscale HTTPS (run once per host, requires tailscale up)
timeout 30s tailscale serve --bg 443 http://127.0.0.1:8000
timeout 30s tailscale serve status

# 7) Replace <machine>.ts.net with your node DNS name from `tailscale status`
timeout 20s curl -kfsS https://<machine>.ts.net/healthz
```

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

Start the API server:

```bash
timeout 120s uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> For an interactive dev loop, run `uvicorn ... --reload` in your own terminal session (no timeout), then stop with `Ctrl+C`.

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

## Production-style loopback run (for SSH or Tailscale serve)

Create env file once:

```bash
cp config/env/.env.example config/env/.env
```

Start loopback profile (API bound to localhost):

```bash
timeout 180s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile loopback up -d
```

Default binding is `127.0.0.1:8000`. To use a different local port (example `8001`):

```bash
API_BIND_PORT=8001 timeout 180s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile loopback up -d
```

## Tailscale connectivity

If you want your Tailnet hostname (for example `https://<machine>.ts.net/`) to reach this API, forward Tailscale HTTPS traffic to local API port 8000:

```bash
timeout 30s tailscale serve --bg 443 http://127.0.0.1:8000
```

Check serve config:

```bash
timeout 30s tailscale serve status
```

If you are using a non-default local port (for example 8001), update serve target accordingly:

```bash
timeout 30s tailscale serve --bg 443 http://127.0.0.1:8001
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

5) Tailscale endpoint responds (replace hostname):

```bash
timeout 20s curl -kfsS https://<machine>.ts.net/healthz
```

6) If something fails, inspect logs:

```bash
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane postgres redis
```

7) If `curl` says **connection refused** on both `8000` and `8001`, the API container likely crashed during startup. Rebuild and relaunch, then re-check logs:

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

## Recommended rollout order (quick start)

Execute in this order for progressive rollout by environment:

1. **Dev**
   - Enable one domain flag at a time.
   - Validate idempotency + reproducibility using deterministic test inputs.
2. **Staging**
   - Promote the same flag and verify monotonic status progression (`queued -> running -> degraded|succeeded|failed`).
   - Confirm schema/version compatibility with downstream consumers.
3. **Prod canary**
   - Route a small capital slice/orders to the newest strategy version first (canary-only traffic).
   - Monitor predefined guardrail metrics during the canary window (risk limits, error-rate, latency, and fill-quality).
   - Auto-rollback to the prior strategy version on any guardrail breach and notify the primary on-call immediately.
4. **Prod full rollout**
   - Require explicit post-canary approval (trading + risk owner) before increasing traffic beyond canary.
   - Keep remaining domains disabled until prior domain is stable.
