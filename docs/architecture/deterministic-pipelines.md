# Deterministic Pipeline Contract

This contract defines minimum execution guarantees for production and pre-production pipelines across worker-research, portfolio-state, graph, and health dependency checks.

## 1) Idempotency requirements

- Every externally-triggered run **must** accept an idempotency key (`request_id`, `run_id`, or equivalent).
- Replays with the same key and semantically equivalent input **must not** create duplicate side effects.
- Writes to persistent state must use upsert/compare-and-swap semantics where feasible.
- Any non-idempotent side effect (notifications, webhooks, third-party writes) must be guarded by a dedupe record.

## 2) Reproducibility rules

- Inputs to execution must be snapshot-addressable (versioned configs, explicit dataset windows, immutable artifact references).
- Runtime decisions must be derivable from persisted metadata (model/task versions, feature flags, dependency versions).
- Randomness must be seeded and the seed captured in run metadata.
- Time-based logic must use explicit timestamps captured at orchestration start; avoid implicit `now()` calls deep in domain logic.

## 3) Monotonic status progression

- Status transitions must be monotonic and forward-only.
- Recommended lifecycle: `queued -> running -> degraded | succeeded | failed`.
- Terminal states are `succeeded`, `failed`, and `degraded`; no transition out of terminal states except explicit operator reset.
- Retries create a new attempt record while preserving parent run identity and prior attempt history.

## 4) Schema/version compatibility expectations

- Producers must emit explicit schema versions in payloads/events.
- Consumers must tolerate at least one prior compatible version during rollout windows.
- Breaking changes require a version bump and dual-read/dual-write migration window.
- Artifact and API contracts must include compatibility notes and deprecation timelines.

## 5) Standard fallback policy

When a production path is disabled by rollout flag or required dependencies are unavailable:

1. Do not fail closed by default if a safe degraded behavior exists.
2. Return/record status `degraded`.
3. Emit a structured reason object with this shape:

```json
{
  "code": "prod_path_disabled|dependency_unavailable",
  "domain": "worker_research|portfolio|graph|health",
  "flag": "GB_<DOMAIN>_PROD_<...>_ENABLED",
  "dependency": "optional dependency identifier",
  "message": "human-readable summary",
  "observed_at": "RFC3339 timestamp",
  "retryable": true
}
```

4. Continue with deterministic fallback behavior (cached snapshot, mock topology, stale-but-valid prior result, or no-op check) and annotate outputs as degraded.
5. Ensure telemetry increments a domain-specific degraded counter for rollout visibility.

## 6) Rollout model (dev -> staging -> prod)

- **Dev**: Enable a single domain prod-path flag for validation with synthetic/sandbox dependencies.
- **Staging**: Enable the same flag with production-like dependencies and confirm deterministic guarantees.
- **Prod**: Enable after staging soak and fallback-path observability are verified.

Rollout should be one domain at a time to isolate risk and simplify rollback.
