# worker-research

Placeholder package for the component at path `services/worker-research`.

## Purpose

This directory is reserved for future implementation.

## Status

- Skeleton only.
- No domain implementation logic yet.

## Production rollout flag

- `GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED` (default: `false`)

When disabled, worker-research must execute the deterministic fallback policy:

- mark run status as `degraded`,
- include a structured reason (`code`, `domain`, `flag`, `message`, `observed_at`, `retryable`),
- continue via deterministic fallback behavior.

See shared contract: `docs/architecture/deterministic-pipelines.md`.

## Recommended rollout sequence

1. **Dev**: enable `GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED=true` and validate idempotent replays.
2. **Staging**: soak with production-like dependencies; verify monotonic status progression.
3. **Prod**: enable after staging is stable and degraded telemetry is visible.
