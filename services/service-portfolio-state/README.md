# service-portfolio-state

Placeholder package for the component at path `services/service-portfolio-state`.

## Purpose

This directory is reserved for future implementation.

## Status

- Skeleton only.
- No domain implementation logic yet.

## Production rollout flag

- `GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED` (default: `false`)

When disabled or dependencies are unavailable, portfolio-state must use deterministic fallback:

- emit `degraded` status,
- attach structured reason metadata,
- return the best deterministic fallback snapshot/no-op response.

See shared contract: `docs/architecture/deterministic-pipelines.md`.

## Recommended rollout sequence

1. **Dev**: enable `GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED=true` and validate reproducible snapshots.
2. **Staging**: verify schema/version compatibility against production-like downstreams.
3. **Prod**: enable after staging soak and fallback observability checks pass.
