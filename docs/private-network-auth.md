# Private single-user deployment: token auth + SSH access

This repository supports a pragmatic private deployment model for a single trusted operator:

- API is reachable only through localhost binding or SSH tunnel.
- Postgres and Redis stay internal to the Docker network.
- Non-health API endpoints require a bearer token.
- Local-only desktop/browser frontend does not collect, store, or attach API bearer tokens.

## 1) Configure API bearer token auth

`apps/api-control-plane` now reads:

- `GB_API_AUTH_TOKEN`: legacy static bearer token (fallback path).
- `GB_API_AUTH_SCOPE`: legacy fallback scopes for `GB_API_AUTH_TOKEN`.
- `GB_API_AUTH_TOKENS`: structured token records for rotation + scoped enforcement in format:
  - `token_id|token_secret|scope_csv|expires_at_iso8601;token_id|...`
  - Example: `primary|token-a|control-plane:read,control-plane:write|2026-05-01T00:00:00Z`
- `GB_API_AUTH_REVOKED_TOKEN_IDS`: comma-separated token IDs to revoke immediately.
- `GB_API_AUTH_ROTATION_INTERVAL_DAYS`: policy interval for scheduled rotation (default `30` days).

Behavior:

- `GET /api/v1/health` and `/healthz` stay unauthenticated for liveness checks.
- All other API routes require `Authorization: Bearer <token>` when any auth token config is set.
- Backend supports dual-accept mode during migration by setting two records in `GB_API_AUTH_TOKENS`.
- Expired/revoked tokens return `401` with `auth_result` classification for expiry/re-auth UX.

## 2) Production compose posture

Use `infra/compose/docker-compose.prod.yml`.

Security-relevant defaults:

- `api-control-plane` publishes only `127.0.0.1:8000:8000`.
- `postgres` and `redis` are **not** published; they are internal-only via Docker networking (`expose`, no `ports`).

Start example:

```bash
GB_API_AUTH_TOKEN='replace-with-long-random-token' \
POSTGRES_PASSWORD='replace-with-strong-password' \
docker compose -f infra/compose/docker-compose.prod.yml up -d
```

## 3) Local-only desktop token handling

Local-only desktop/browser settings no longer collect or store API bearer tokens, and the local-only HTTP client does not attach `Authorization` headers. Use an unauthenticated local API configuration for this mode, or access protected private deployments with an external client that can provide the required bearer token.

## 4) SSH tunnel access pattern

For remote hosts, keep API bound to loopback and tunnel from your workstation:

```bash
ssh -N -L 8000:127.0.0.1:8000 user@your-server
```

Then set Desktop API base URL to:

- `http://127.0.0.1:8000/api/v1`

This avoids opening inbound API ports publicly while preserving operator access.

## 5) Rotation / maintenance checklist

- Rotation interval: rotate active tokens every **30 days** (or faster per incident response).
- Use dual-accept migration window:
  1. Add new token record in `GB_API_AUTH_TOKENS` (old + new both present).
  2. Update external protected-route clients to the new value.
  3. Confirm no legacy token usage in audit logs.
  4. Remove old token and optionally add old `token_id` to `GB_API_AUTH_REVOKED_TOKEN_IDS`.
- Revocation procedure:
  1. Add compromised `token_id` to `GB_API_AUTH_REVOKED_TOKEN_IDS`.
  2. Roll/replace credential for affected clients.
  3. Monitor `auth_result=revoked_token` and `auth_result=invalid_token` during cleanup.
- Rotate `POSTGRES_PASSWORD` with planned maintenance.
- Keep this document and `docker-compose.prod.yml` in sync when auth model evolves (e.g., moving from static token to scoped/JWT auth).

## 6) TLS trust assumptions by deployment mode

- **Localhost (`http://127.0.0.1` / loopback only):**
  - HTTP allowed for local dev and SSH local-forwarded sessions.
  - Never expose loopback-only API socket directly to public interfaces.
- **Tailscale HTTPS:**
  - Prefer HTTPS endpoint with trusted cert chain even on Tailnet.
  - Application auth stays mandatory; Tailnet transport is not an auth substitute.
- **Reverse proxy TLS termination:**
  - TLS terminates at edge proxy with TLS 1.2+ (TLS 1.3 preferred).
  - Enforce sanitized forwarding headers and trusted-hop rules.
  - Upstream app auth checks stay enabled behind the proxy.
