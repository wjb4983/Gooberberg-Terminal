# Server deployment runbook (Docker Compose production)

This runbook deploys the control plane using hardened defaults from `infra/compose/docker-compose.prod.yml`.

## 1) Prerequisites

- Linux host with Docker Engine + Docker Compose plugin.
- Firewall defaults set to deny inbound by default.
- Repository checked out on server.
- DNS pointed to host (if using `nginx` profile).

## 2) Prepare environment

1. Copy the production environment template:
   ```bash
   cp config/env/.env.example config/env/.env
   ```
2. Edit `config/env/.env` and set strong values for:
   - `GB_API_AUTH_TOKEN`
   - `POSTGRES_PASSWORD`
3. Keep `.env` out of version control.

## 3) Review exposure model (deny-by-default)

- Default `docker-compose.prod.yml` exposes **no public API port**.
- `postgres` and `redis` are internal-only (`expose`, no host `ports`).
- Choose one access mode:
  - **Recommended:** `nginx` profile for controlled TLS ingress on 80/443.
  - **Alternative:** `loopback` profile for 127.0.0.1-only API access.

## 4) TLS placeholders for nginx profile

If using profile `nginx`:

1. Replace certificate placeholders:
   - `/etc/nginx/certs/fullchain.pem`
   - `/etc/nginx/certs/privkey.pem`
2. Update `infra/nginx/nginx.prod.conf` `server_name` values.
3. (Optional) integrate certbot/acme automation for renewals.

## 5) Validate compose configuration

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml config >/tmp/gb-prod.compose.rendered.yaml
```

## 6) Deploy

### Option A: Reverse proxy with TLS (recommended)

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile nginx up -d
```

### Option B: Loopback-only API (SSH tunnel / local proxy)

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml --profile loopback up -d
```

## 7) Post-deploy checks

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
```

For loopback mode:

```bash
timeout 20s curl -fsS http://127.0.0.1:${API_BIND_PORT:-8000}/healthz
```

For nginx mode:

```bash
timeout 20s curl -kfsS https://<your-domain>/healthz
```

## 8) Operations

Tail logs:

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=200 api-control-plane postgres redis
```

Update images + restart:

```bash
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml pull
timeout 120s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml up -d
```

Stop stack:

```bash
timeout 60s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml down
```

## 9) Rollback

1. Pin image tags in compose to known-good versions.
2. Redeploy with the same `docker compose ... up -d` command.
3. If needed, restore database from backups before reintroducing traffic.
