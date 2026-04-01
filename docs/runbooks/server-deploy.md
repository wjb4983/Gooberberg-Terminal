# Server deployment runbook (Docker Compose production)

This runbook deploys the control plane using hardened defaults in `infra/compose/docker-compose.prod.yml`.

## 1) Prerequisites

- Linux host with Docker Engine + Compose plugin.
- Default-deny host firewall policy.
- Repository checked out on server.
- DNS routed to host (if using `nginx` profile).

## 2) Prepare environment

```bash
cp config/env/.env.example config/env/.env
```

Edit `config/env/.env` and set strong values:

- `GB_API_AUTH_TOKEN`
- `POSTGRES_PASSWORD`
- (Optional hardening) explicit `GB_APP_VERSION`, `GB_API_PREFIX`, ports.

## 3) Understand runtime paths

### Fast path in production

- Operator/API client submits JSON control-plane commands (jobs, risk, strategy, model actions).
- API responds quickly and emits WS events.
- Redis stores queue/state for quick retrieval.

### Slow path in production

- Worker services consume queued jobs and perform heavyweight execution.
- Completed outputs are represented via references (`result_ref`, `artifact_ref`), not inlined heavy data.

## 4) Exposure model (deny-by-default)

- Base compose service does **not** publish API publicly.
- `postgres` and `redis` are internal-only (`expose`, no host `ports`).
- Choose one ingress mode:
  - **Recommended:** `nginx` profile with TLS.
  - **Alternative:** `loopback` profile with `127.0.0.1` binding only.

## 5) TLS placeholders for nginx profile

If using profile `nginx`:

1. Replace cert placeholders:
   - `/etc/nginx/certs/fullchain.pem`
   - `/etc/nginx/certs/privkey.pem`
2. Update `infra/nginx/nginx.prod.conf` `server_name`.
3. Optionally integrate cert automation.

## 6) Validate compose rendering

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml config >/tmp/gb-prod.compose.rendered.yaml
```

## 7) Deploy

### Option A: nginx profile (recommended)

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile nginx up -d
```

### Option B: loopback-only API

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile loopback up -d
```

## 8) Post-deploy checks

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
```

Loopback check:

```bash
timeout 20s curl -fsS http://127.0.0.1:${API_BIND_PORT:-8000}/healthz
```

nginx check:

```bash
timeout 20s curl -kfsS https://<your-domain>/healthz
```

API contract check:

```bash
timeout 20s curl -fsS https://<your-domain>/api/v1/health -H "Authorization: Bearer $GB_API_AUTH_TOKEN"
```

## 9) Operations

Tail logs:

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=200 api-control-plane postgres redis
```

Rolling refresh:

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml pull
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml up -d
```

Graceful stop:

```bash
timeout 60s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml down
```

## 10) Troubleshooting (server)

### API failures

- Check container health and logs first.
- Confirm auth token alignment between clients and `GB_API_AUTH_TOKEN`.
- Validate prefix consistency (`GB_API_PREFIX`, default `/api/v1`).

### WebSocket failures

- Verify reverse proxy forwards upgrade headers correctly.
- Confirm client subscribes to valid topics.
- Inspect API logs for connection churn and malformed message errors.

### Redis failures

- Validate `redis` container health (`redis-cli ping` inside container if needed).
- If Redis unavailable, API may run in in-memory fallback (degraded durability/continuity).
- Confirm network reachability and DSN (`GB_REDIS_DSN`).

### Postgres failures

- Confirm `postgres` container is healthy and credentials match DSN.
- Validate DSN from API environment (`GB_POSTGRES_DSN`).
- Note: current `/api/v1/health` Postgres/Redis reachability fields are placeholders; rely on container health/logs for definitive status.

## 11) Rollback

1. Pin image tags to known-good versions.
2. Re-run `docker compose ... up -d` with pinned tags.
3. Restore database backup if schema/data incompatibility occurred.
4. Re-enable traffic only after health/API/WS checks pass.
