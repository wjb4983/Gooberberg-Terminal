# @gb/desktop-tauri

Initial Tauri + React + TypeScript desktop shell.

## Implemented

- Route-based shell with pages: Dashboard, Jobs, Strategies, Portfolio, Graph, Settings.
- Dashboard widget that fetches `GET /health` using a typed API client.
- Settings page for API base URL + token.
- Local persistence for non-sensitive preferences (`baseUrl`).
- Tauri Rust bootstrap with `save_api_token` command as secure storage integration point.

## Development

```bash
pnpm --filter @gb/desktop-tauri dev
```

## Tauri

Rust sources are in `src-tauri/` and intentionally minimal.
