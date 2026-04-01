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
  desktop-tauri/
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

## Status

- ✅ Skeleton structure created.
- ✅ Documentation baseline established.
- 🚧 Domain implementation intentionally deferred.
