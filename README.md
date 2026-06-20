# Gooberberg Terminal Monorepo

A greenfield monorepo skeleton for a quantitative research and trading platform. This repository is intentionally scaffold-only: it provides production-style structure, ownership boundaries, and documentation without implementation logic.

## Architecture Summary

The platform separates **research velocity** from **live-trading safety**:

- **Fast path (research loop):** Rapid idea iteration, backtests, feature engineering, and model experimentation.
- **Slow path (live execution):** Controlled, auditable, policy-gated promotion and execution in production.

### Fast Path

The fast path optimizes for throughput and experimentation:

- `services/worker-research` for ad hoc and batch quant research jobs.
- `services/worker-training` for model training and offline evaluation.
- `services/service-data` for ingestion/normalization interfaces and historical data workflows.
- Python shared libs in `libs/py/*` for reusable domain primitives, IO, and client abstractions.

### Slow Path

The slow path optimizes for correctness, controls, and resilience:

- `apps/api-control-plane` as the operator/API boundary for configuration, approvals, and promotion workflows.
- `services/service-inference-live` for live model inference interfaces.
- `services/service-portfolio-state` for canonical portfolio/account state services.
- `services/service-risk-exec` as centralized risk gate + execution authority.
- `services/orchestrator` for policy-aware workflow sequencing and coordination.

### Central Risk & Execution Authority

`services/service-risk-exec` is the **single authority** for order-risk checks and execution routing in production. No other component should directly bypass this boundary for live trade placement. This keeps risk policy enforcement centralized, testable, and auditable.

## Repository Map

```text
apps/
  desktop-tauri/  # Browser/Vite frontend workspace; package remains @gb/desktop-tauri until a future apps/web migration.
  api-control-plane/

services/
  orchestrator/
  worker-research/
  worker-training/
  service-inference-live/
  service-portfolio-state/
  service-risk-exec/
  service-data/

libs/
  py/
    gb_core/
    gb_io/
    gb_clients/
  ts/
    @gb/
      schemas/
      api-client/
      ui-components/

infra/
  compose/
  docker/

config/
  env/
  risk/

scripts/
docs/
  runbooks/
```


## Local frontend development

The canonical local frontend is the browser-based Vite app. The workspace still lives at `apps/desktop-tauri` and keeps the package name `@gb/desktop-tauri` for now to avoid a large rename; a later cleanup can migrate it to `apps/web`.

Recommended quick-start order:

1. Start backend dependencies and the API control plane:

   ```bash
   timeout 120s docker compose -f infra/compose/docker-compose.dev.yml up --build api-control-plane postgres redis
   ```

2. Start the browser frontend with Vite in a second terminal:

   ```bash
   timeout 120s pnpm --filter @gb/desktop-tauri dev -- --host 0.0.0.0
   ```

3. Open the VS Code forwarded frontend URL for port `1420`.

4. Run the finite local full-stack smoke check from another terminal:

   ```bash
   timeout 60s scripts/dev/check-local-fullstack.sh
   ```

5. Stop the local stack when you are done:

   ```bash
   timeout 60s docker compose -f infra/compose/docker-compose.dev.yml down --remove-orphans
   ```

Packaged desktop/Tauri builds have been removed from the default workflow; use the Vite browser frontend for local UI development.

## Status

- ✅ Skeleton structure created.
- ✅ Documentation baseline established.
- 🚧 Domain implementation intentionally deferred.

## Local browser access

- Backend CORS defaults support local browser access from `http://127.0.0.1:1420` and `http://localhost:1420`. Packaged Tauri origins are no longer part of the default release workflow.
- See `docs/runbooks/local-server-browser.md` for local backend/frontend ports, browser access, and VS Code port-forward guidance.
