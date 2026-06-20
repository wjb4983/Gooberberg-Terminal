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

For local desktop development, start the full stack from the repository root:

```bash
pnpm dev:local
```

The local full-stack script starts Vite on port `1420` with `--host 0.0.0.0` so browser-based environments can reach the dev frontend. In VS Code, open or forward port `1420`, then browse to the forwarded frontend URL shown by VS Code.

If you start the desktop frontend directly and need Vite to bind to a non-default host, set `GB_VITE_HOST` before running Vite:

```bash
GB_VITE_HOST=0.0.0.0 pnpm --filter @gb/desktop-tauri dev
```

The default browser-facing API base URL remains `http://localhost:8000`. Change it only from the desktop Settings page when using a tailnet, proxy, or other API endpoint.

## Tauri

Rust sources are in `src-tauri/` and intentionally minimal.
