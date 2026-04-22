# Tailscale connectivity runbook

This runbook covers how to expose and validate the API over your tailnet, then verify client access for both HTTP and WebSocket traffic.

## 1) Server flow

### 1.1 Verify API locally first

Before mapping anything through Tailscale, confirm the server is healthy on loopback:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz

timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

If these fail, fix local service/container issues before continuing.

### 1.2 Map tailnet traffic to local API

Use one of these patterns:

#### Option A: `tailscale serve` (simple)

```bash
# Map tailnet HTTPS :443 -> local API :8000
timeout 20s tailscale serve --https=443 http://127.0.0.1:8000

# Verify mapping
timeout 20s tailscale serve status
```

#### Option B: Reverse proxy + Tailscale ingress

If you already run nginx/Caddy/Traefik locally, route Tailscale traffic to that proxy and ensure it forwards:

- `GET /healthz`
- `GET /api/v1/health`
- `GET /ws` with WebSocket upgrade headers.

### 1.3 Obtain machine tailnet DNS/IP

Get the canonical machine identity clients should use:

```bash
# Machine name + tailnet DNS + Tailscale IPs
timeout 20s tailscale status --self

# Direct Tailscale IPv4
timeout 20s tailscale ip -4
```

Use the machine DNS name (for example `<machine>.<tailnet>.ts.net`) when possible; prefer it over raw IP to avoid client reconfiguration when node IPs rotate.

## 2) Client flow

Assume:

- `TS_HOST=<machine>.<tailnet>.ts.net`
- `TOKEN=<GB_API_AUTH_TOKEN>`

### 2.1 Exact health URLs

Health endpoints are unauthenticated and should return `200` when reachable:

```bash
timeout 20s curl -kfsS "https://${TS_HOST}/healthz"
timeout 20s curl -kfsS "https://${TS_HOST}/api/v1/health"
```

### 2.2 Authenticated non-health requests (bearer token)

Non-health API routes require exact bearer auth when token auth is enabled:

```bash
timeout 20s curl -kfsS "https://${TS_HOST}/api/v1/models/deployments" \
  -H "Authorization: Bearer ${TOKEN}"
```

If you receive `401`/`403`, verify token value and header formatting exactly.

### 2.3 WebSocket URL format

WebSocket endpoint path is `/ws`:

- `wss://<machine>.<tailnet>.ts.net/ws` (recommended through Tailscale HTTPS)
- `ws://<tailscale-ip>:8000/ws` (direct/non-TLS only when intentionally allowed)

After connect, send your subscription message per app protocol and confirm event delivery.

## 3) Troubleshooting matrix

| Symptom | Likely cause | Checks | Fix |
|---|---|---|---|
| `connection refused` | API not listening, serve/proxy not mapped, firewall/ACL block | `timeout 20s curl -fsS http://127.0.0.1:8000/healthz`; `timeout 20s tailscale serve status`; `timeout 20s tailscale status --self` | Start/restart API, correct `tailscale serve` mapping, open required ACL/firewall path. |
| `401` / `403` on non-health route | Missing/incorrect bearer token or wrong environment token | Re-run with `-H "Authorization: Bearer ${TOKEN}"`; compare with server `GB_API_AUTH_TOKEN` | Rotate/set correct token, update client secret store, retry request. |
| WebSocket disconnects/churn | Proxy missing upgrade headers, idle timeout, unstable route | Validate `/ws` path routing; inspect proxy/API logs; test with minimal client over `wss://.../ws` | Enable upgrade headers + longer timeouts, stabilize route, reconnect with backoff. |
| Stale DNS / wrong tailnet host | Client using outdated machine name/IP or connected to different tailnet | `timeout 20s tailscale status --self`; compare client `TS_HOST`; test both DNS and current tailnet IP | Switch client to correct `<machine>.<tailnet>.ts.net`, flush DNS cache if needed, ensure both peers are in same tailnet. |

## 4) Related runbooks

- [Server deployment runbook](./server-deploy.md)
- [Incident response runbook](./incident-response.md)
- [Private network auth](../private-network-auth.md)
