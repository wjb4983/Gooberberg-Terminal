# Private single-user deployment: token auth + SSH access

This repository supports a pragmatic private deployment model for a single trusted operator:

- API is reachable only through localhost binding or SSH tunnel.
- Postgres and Redis stay internal to the Docker network.
- Non-health API endpoints require a bearer token.
- Desktop stores token in OS secure credential storage (keychain/credential manager/libsecret).

## 1) Configure API bearer token auth

`apps/api-control-plane` now reads:

- `GB_API_AUTH_TOKEN` (required in production): static bearer token for v1 validation.
- `GB_API_AUTH_SCOPE` (optional): scope placeholder (`control-plane:full` default) returned in auth responses and available for future policy checks.

Behavior:

- `GET /api/v1/health` and `/healthz` stay unauthenticated for liveness checks.
- All other API routes require `Authorization: Bearer <GB_API_AUTH_TOKEN>` when `GB_API_AUTH_TOKEN` is set.

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

## 3) Desktop token handling

Desktop settings save the API token through Tauri command bridge into OS secure storage.

- Rust command: `save_api_token`
- Rust command: `get_api_token`
- Backing store: system keychain/credential vault via `keyring` crate.

The desktop HTTP client reads the stored token and sends `Authorization: Bearer ...` on requests.

## 4) SSH tunnel access pattern

For remote hosts, keep API bound to loopback and tunnel from your workstation:

```bash
ssh -N -L 8000:127.0.0.1:8000 user@your-server
```

Then set Desktop API base URL to:

- `http://127.0.0.1:8000/api/v1`

This avoids opening inbound API ports publicly while preserving operator access.

## 5) Rotation / maintenance checklist

- Rotate `GB_API_AUTH_TOKEN` periodically and after any workstation compromise.
- Rotate `POSTGRES_PASSWORD` with planned maintenance.
- Keep this document and `docker-compose.prod.yml` in sync when auth model evolves (e.g., moving from static token to scoped/JWT auth).
