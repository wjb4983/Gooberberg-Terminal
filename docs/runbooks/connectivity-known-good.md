# Connectivity Known-Good Endpoint Matrix

This runbook is the **entry-gate triage checklist** before any deeper desktop/API debugging.

Use it to confirm:
- API process/container is up and bound to expected interface+port.
- Browser or desktop local base URL targets `http://127.0.0.1:8000`.
- HTTP health probes return expected JSON.
- Auth token mode alignment (`GB_API_AUTH_TOKEN` vs desktop keychain token).
- WebSocket URL path/scheme resolves and upgrades.

## 0) Local endpoint reference

| Service | Bind expectation | Browser/API URL | WS URL | Auth expectation |
|---|---|---|---|---|
| Backend API | `127.0.0.1:8000` | `http://127.0.0.1:8000` | `ws://127.0.0.1:8000/ws` | Health routes are unauthenticated. Non-health routes require bearer token only when `GB_API_AUTH_TOKEN` is set. |
| Frontend dev server | `127.0.0.1:1420` | `http://127.0.0.1:1420` or VS Code forwarded port `1420` | n/a | Uses local backend configuration. |

## 1) Verify API process/container + bind target

### A. Dev compose

```bash
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml ps api-control-plane
timeout 30s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane
```

Expected: running container and no startup crash loop.

### B. Host bind check (local loopback profile)

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
```

Expected: JSON `{"status":"ok"}`.

If using prod loopback profile, expected bind is `127.0.0.1:${API_BIND_PORT:-8000}`.

### C. Desktop endpoint alignment

Desktop/browser default preference is `http://localhost:8000`; update Settings only if using another local API base URL.

When using `pnpm dev:local` in VS Code or a remote browser environment, Vite serves the frontend on port `1420`. Open or forward port `1420` in VS Code, then browse to the forwarded frontend URL. Keep the API base URL set to `http://localhost:8000` unless your local Settings profile intentionally points at a different local API endpoint.

## 2) Validate HTTP path from desktop host

Run all three probes from the **same machine/runtime context as desktop app**:

```bash
BASE_URL="http://127.0.0.1:8000"

timeout 20s curl -fsS "$BASE_URL/healthz"
timeout 20s curl -fsS "$BASE_URL/api/v1/health"
timeout 20s curl -fsS "$BASE_URL/api/v1/health/queue"
```

Expected payload shapes:
- `/healthz` returns `{"status":"ok"}`.
- `/api/v1/health` returns service/version plus dependency objects (`postgres`, `redis`).
- `/api/v1/health/queue` returns queue status and heartbeat metadata.

If any probe fails, stop rollout and restore the last known-good local endpoint before proceeding.

## 3) Validate auth mode (`GB_API_AUTH_TOKEN`)

1. Check server-side mode:

```bash
timeout 10s bash -lc 'printf "%s\n" "GB_API_AUTH_TOKEN=${GB_API_AUTH_TOKEN:+set}"'
```

2. Behavior expectations:
   - If token is **unset**: non-health routes are open (subject to route logic).
   - If token is **set**: all non-health routes require exact `Authorization: Bearer <token>`.

3. Desktop checks:
   - Ensure token is saved in OS keychain via desktop token flow.
   - Confirm client attaches `Authorization` for non-health routes and skips health routes.

4. Quick verification:

```bash
TOKEN="<expected-token>"
timeout 20s curl -i -fsS "$BASE_URL/api/v1/jobs" -H "Authorization: Bearer $TOKEN"
```

Expected: non-401 response when token is correct (or route-specific status), and `401` when missing/incorrect in token-required environments.

## 4) Validate WebSocket URL path and scheme

Path must be `/ws`: `ws://127.0.0.1:8000/ws`.

Sanity-check upgrade (HTTP side):

```bash
timeout 20s curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  "$BASE_URL/ws"
```

Then validate a real WS client can connect and subscribe at least one topic (for example `jobs`) from desktop runtime context.

## 5) Green triage checklist (gate)

Proceed only when all are green:
- [ ] API process/container running and bound to expected interface/port.
- [ ] Desktop/browser `baseUrl` matches the local endpoint.
- [ ] `GET /healthz` returns expected JSON.
- [ ] `GET /api/v1/health` returns expected JSON.
- [ ] `GET /api/v1/health/queue` returns expected JSON.
- [ ] Auth mode validated (`GB_API_AUTH_TOKEN` vs desktop keychain token).
- [ ] WS URL resolves with the local `ws://` scheme.
- [ ] WS session opens and subscribes to at least one topic.

Rollback if red: revert to last known-good local endpoint config and freeze new changes until connectivity is green.
