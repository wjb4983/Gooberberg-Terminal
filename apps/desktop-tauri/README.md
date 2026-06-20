# @gb/desktop-tauri

Initial Tauri + React + TypeScript desktop shell.

## Implemented

- Route-based shell with pages: Dashboard, Jobs, Models, Strategies, Portfolio, Graph, Alerts & Health, Settings.
- Dashboard widget that fetches `GET /api/v1/health` using shared `@gb/api-client` and `@gb/schemas` contracts.
- Settings page for API base URL + token.
- Local persistence for non-sensitive preferences (`baseUrl`).
- Tauri Rust commands (`save_api_token`, `get_api_token`) backed by OS secure credential storage.
- HTTP requests include `Authorization: Bearer <token>` when a token is present in secure storage.

## Development

For local desktop development, run these tasks from the repository root in order:

1. Start the backend/API dependencies and Vite together:

   ```bash
   timeout 20m pnpm dev:local
   ```

2. In a second terminal, verify the finite local smoke checks:

   ```bash
   timeout 60s pnpm dev:local:check
   ```

3. Open or forward port `1420`, then browse to the forwarded frontend URL shown by your editor or terminal.

The local full-stack script starts Vite on port `1420` with `--host 0.0.0.0` so browser-based environments can reach the dev frontend. It also records a local queue heartbeat so the status bar does not report a false queue/worker degradation while you are developing without a separate worker process.

If you start the desktop frontend directly, start and validate the API first, then bind Vite to the host you need:

```bash
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
GB_VITE_HOST=0.0.0.0 pnpm --filter @gb/desktop-tauri dev
```

The default API base URL is `http://127.0.0.1:8000`. Change it only from the desktop Settings page when using a tailnet, proxy, or other API endpoint.

## Tauri

Rust sources are in `src-tauri/` and intentionally minimal.
