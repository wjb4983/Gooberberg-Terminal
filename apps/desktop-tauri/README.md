# @gb/desktop-tauri

Browser-first Vite + React + TypeScript frontend. The package and path still use `desktop-tauri` to avoid a large rename during the initial browser frontend workflow; a future migration may move this workspace to `apps/web`.

## Implemented

- Route-based shell with pages: Dashboard, Jobs, Models, Strategies, Portfolio, Graph, Alerts & Health, Settings.
- Dashboard widget that fetches `GET /api/v1/health` using shared `@gb/api-client` and `@gb/schemas` contracts.
- Settings page for API base URL + token.
- Local persistence for non-sensitive preferences (`baseUrl`).
- Browser-compatible token and preference storage with Tauri command fallbacks when the app is packaged as desktop.
- HTTP requests include `Authorization: Bearer <token>` when a token is present in storage.

## Development

For local browser frontend development, run these tasks from the repository root in the recommended order:

1. Start the Vite/browser frontend:

   ```bash
   timeout 20m pnpm dev:frontend
   ```

2. For a full local stack, start the backend/API dependencies and Vite together:

   ```bash
   timeout 20m pnpm dev:local
   ```

3. In a second terminal, verify the finite local smoke checks:

   ```bash
   timeout 60s pnpm dev:local:check
   ```

4. Open or forward port `1420`, then browse to the forwarded frontend URL shown by your editor or terminal.

The local full-stack script starts Vite on port `1420` with `--host 0.0.0.0` so browser-based environments can reach the dev frontend. It also records a local queue heartbeat so the status bar does not report a false queue/worker degradation while you are developing without a separate worker process.

If you start the browser frontend directly against a local API, start and validate the API first, then bind Vite to the host you need:

```bash
timeout 240s docker compose -f infra/compose/docker-compose.dev.yml up -d --build postgres redis api-control-plane
timeout 20s curl -fsS http://127.0.0.1:8000/healthz
timeout 20s curl -fsS http://127.0.0.1:8000/api/v1/health
GB_VITE_HOST=0.0.0.0 timeout 20m pnpm --filter @gb/desktop-tauri dev
```

The default API base URL is `http://127.0.0.1:8000`. Change it only from the Settings page when using a tailnet, proxy, or other API endpoint.

## Tauri

Tauri remains available for desktop packaging experiments via `pnpm --filter @gb/desktop-tauri tauri:dev` and `pnpm --filter @gb/desktop-tauri tauri:build`, but Vite/browser is the canonical local frontend workflow. Rust sources are in `src-tauri/` and intentionally minimal.
