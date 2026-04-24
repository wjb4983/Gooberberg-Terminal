# Connectivity Known-Good Endpoint Matrix

This runbook is the **entry-gate triage checklist** before any deeper desktop/API debugging.

Use it to confirm:
- API process/container is up and bound to expected interface+port.
- Desktop `baseUrl` targets the same endpoint profile.
- HTTP health probes return expected JSON.
- Auth token mode alignment (`GB_API_AUTH_TOKEN` vs desktop keychain token).
- WebSocket URL path/scheme resolves and upgrades.

## 0) Endpoint profile matrix (one-page reference)

| Profile | API bind expectation | Desktop `baseUrl` | Health probe base | WS URL | Auth expectation |
|---|---|---|---|---|---|
| Localhost dev compose | `127.0.0.1:8000` | `http://localhost:8000` | `http://127.0.0.1:8000` | `ws://127.0.0.1:8000/ws` | Health routes are unauthenticated. Non-health routes require bearer token only when `GB_API_AUTH_TOKEN` is set. |
| Tailscale HTTPS | API still local (`127.0.0.1:8000`) and exposed via `tailscale serve` | `https://<machine>.<tailnet>.ts.net` | `https://<machine>.<tailnet>.ts.net` | `wss://<machine>.<tailnet>.ts.net/ws` | Same auth model as above; HTTPS transport does not change token requirements. |
| Reverse proxy (nginx/LB) | Upstream API reachable by proxy at local/service address | `https://<your-domain>` | `https://<your-domain>` | `wss://<your-domain>/ws` | Same auth model; ensure proxy preserves `Authorization` and WS upgrade headers. |

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

Desktop default preference is `http://localhost:8000`; update Settings if using tailnet/proxy endpoint.

## 2) Validate HTTP path from desktop host

Run all three probes from the **same machine/runtime context as desktop app**:

```bash
BASE_URL="http://127.0.0.1:8000"  # or https://<machine>.ts.net or https://<your-domain>

timeout 20s curl -fsS "$BASE_URL/healthz"
timeout 20s curl -fsS "$BASE_URL/api/v1/health"
timeout 20s curl -fsS "$BASE_URL/api/v1/health/queue"
```

Expected payload shapes:
- `/healthz` returns `{"status":"ok"}`.
- `/api/v1/health` returns service/version plus dependency objects (`postgres`, `redis`).
- `/api/v1/health/queue` returns queue status and heartbeat metadata.

If any probe fails, stop rollout and restore last known-good endpoint/profile before proceeding.

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

Path must be `/ws` for all profiles.

- Localhost: `ws://127.0.0.1:8000/ws`
- Tailscale HTTPS: `wss://<machine>.<tailnet>.ts.net/ws`
- Reverse proxy HTTPS: `wss://<your-domain>/ws`

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
- [ ] Desktop `baseUrl` matches selected endpoint profile.
- [ ] `GET /healthz` returns expected JSON.
- [ ] `GET /api/v1/health` returns expected JSON.
- [ ] `GET /api/v1/health/queue` returns expected JSON.
- [ ] Auth mode validated (`GB_API_AUTH_TOKEN` vs desktop keychain token).
- [ ] WS URL resolves with correct `ws://` or `wss://` scheme.
- [ ] WS session opens and subscribes to at least one topic.

Rollback if red: revert to last known-good endpoint/profile config and freeze new changes until connectivity is green.
