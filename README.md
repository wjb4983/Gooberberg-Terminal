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

1. Start the browser frontend with Vite:

   ```bash
   timeout 20m pnpm dev:frontend
   ```

   This is equivalent to the initially supported direct command:

   ```bash
   timeout 20m pnpm --filter @gb/desktop-tauri dev
   ```

2. For a full local stack, start API dependencies and the Vite frontend together:

   ```bash
   timeout 20m pnpm dev:local
   ```

3. In a second terminal, run the finite smoke checks:

   ```bash
   timeout 60s pnpm dev:local:check
   ```

Tauri commands remain available for desktop packaging experiments, but they are not the default local frontend workflow.

## Status

- ✅ Skeleton structure created.
- ✅ Documentation baseline established.
- 🚧 Domain implementation intentionally deferred.

## Security & private deployment

- See `docs/private-network-auth.md` for private single-user deployment guidance, bearer token auth, and SSH tunnel access.
