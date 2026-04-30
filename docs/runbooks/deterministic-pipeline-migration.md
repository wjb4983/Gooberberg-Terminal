# Deterministic Pipeline Migration Runbook

## Quick-start order (recommended)
1. Enable structured stage logs + metrics counters in metrics-only mode.
2. Validate compatibility checks in staging-like restricted environments.
3. Update client integrations to read `response_metadata.version`.
4. Execute phased rollout (Phase 0 -> Phase 3).
5. Keep rollback command ready in each environment.

## Phased rollout
- **Phase 0 (flags off, metrics-only):**
  - Keep all prod-path flags disabled.
  - Confirm stage telemetry fields: `stage`, `duration_ms`, `success`, `fingerprint`, `fallback_reason`.
- **Phase 1 (canary per service):**
  - Enable one service flag at a time for a low-risk slice.
  - Verify deterministic fingerprints are stable across replayed requests.
- **Phase 2 (staging default-on):**
  - Set deterministic flags on by default in staging.
  - Reject ambiguous mixed modes unless `GB_DETERMINISTIC_PIPELINE_MIXED_MODE_ALLOWED=true`.
- **Phase 3 (prod default-on + cleanup):**
  - Enable all deterministic flags in production.
  - Remove legacy non-deterministic paths after soak and incident-free window.

## Rollback triggers
Rollback immediately if any of the following occur:
- Stage failure rate exceeds 2% over 5 minutes for any deterministic stage.
- p95 stage duration regresses by 50%+ from pre-rollout baseline.
- Fingerprint drift detected for replay-equivalent inputs.
- Health stage degrades due to deterministic-only dependency assumptions.

## One-command rollback procedures
- **Development:**
  - `GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED=false GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED=false GB_GRAPH_PROD_TOPOLOGY_ENABLED=false GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED=false uv run app/main.py`
- **Staging:**
  - `kubectl -n staging set env deploy/api-control-plane GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED=false GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED=false GB_GRAPH_PROD_TOPOLOGY_ENABLED=false GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED=false`
- **Production:**
  - `kubectl -n prod set env deploy/api-control-plane GB_WORKER_RESEARCH_PROD_PIPELINE_ENABLED=false GB_PORTFOLIO_PROD_SNAPSHOT_ENABLED=false GB_GRAPH_PROD_TOPOLOGY_ENABLED=false GB_HEALTH_PROD_DEPENDENCY_CHECKS_ENABLED=false`
