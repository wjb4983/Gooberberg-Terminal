# Local server browser runbook

Use this runbook when running Gooberberg locally and opening the app from the built-in VS Code browser, a forwarded port, or your host browser. The supported local topology is:

- Backend API: `http://127.0.0.1:8000`
- Frontend dev server: `http://127.0.0.1:1420`

The backend CORS default supports local browser access from `http://127.0.0.1:1420` and `http://localhost:1420`. Packaged Tauri origins (`tauri://localhost`, `http://tauri.localhost`, and `https://tauri.localhost`) are not enabled by default; add them to `GB_CORS_ALLOWED_ORIGINS` only when you intentionally support packaged Tauri access.

## 1) Start the backend

From the repository root, start the backend stack with the documented ops workflow:

```bash
timeout 30m ./scripts/ops/first-time-build-run.sh
```

For an existing local stack, use:

```bash
timeout 20m ./scripts/ops/subsequent-run.sh
```

After startup, verify the backend health endpoints from the same environment that started the stack:

```bash
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
```

## 2) Start the frontend

Start the local frontend dev server:

```bash
timeout 10m pnpm dev -- --host 127.0.0.1 --port 1420
```

If your package scripts expose a local full-stack helper, prefer the helper for repeatable local development:

```bash
timeout 10m scripts/dev/local-fullstack.sh
```

## 3) Open in VS Code browser or forwarded port

In VS Code or a remote dev container, forward these ports:

1. `1420` for the frontend UI.
2. `8000` for direct backend health/API checks.

Open the frontend with one of these options:

- VS Code **Ports** panel: open forwarded port `1420` in the browser.
- Host browser: open the forwarded URL for port `1420`.
- Same-machine browser: open `http://127.0.0.1:1420`.

Use the forwarded backend URL only for diagnostics. The frontend should continue to target the local backend at `127.0.0.1:8000` unless your development environment explicitly rewrites forwarded-port origins.

## 4) Quick verification order

Run checks in this order so failures point to the right layer:

1. Backend process and dependencies:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/healthz
   ```

2. Backend API route:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
   ```

3. Frontend dev server:

   ```bash
   timeout 20s curl -fsS http://127.0.0.1:1420
   ```

4. Browser access through VS Code port forwarding: open forwarded port `1420` and refresh once after the dev server reports ready.

## 5) Troubleshooting

- **Backend health fails:** inspect compose status and API logs:

  ```bash
  timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
  timeout 45s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=200 api-control-plane postgres redis
  ```

- **Frontend port does not open:** confirm the dev server is bound to `127.0.0.1:1420`, then restart the VS Code port forward for port `1420`.
- **Browser loads but API calls fail:** verify port `8000` is forwarded in VS Code and that browser devtools show requests going to `127.0.0.1:8000` or the expected forwarded backend origin.
- **Stale frontend bundle:** stop the dev server and restart it with the command in step 2.
