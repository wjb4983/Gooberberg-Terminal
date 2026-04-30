# ADR: Event-Sourced Deterministic Decision and Execution Contract

- **Status:** Accepted
- **Date:** 2026-04-30
- **Deciders:** Architecture, Trading Systems, Platform
- **Supersedes:** None
- **Superseded by:** None

## Context

Our downstream modules currently implement parts of provenance, replayability, and safety behavior in inconsistent ways. This creates merge-time ambiguity and operational risk when the system encounters uncertain inputs, partial failures, or asynchronous event delivery.

To guarantee auditable outcomes, reproducible state, and predictable safety controls, we need a single architecture decision that all modules can implement and validate against.

## Decision

All downstream modules MUST implement the following contract.

### 1) Source of truth: append-only, event-sourced history

- Domain truth is the immutable event log, not mutable row snapshots.
- All state projections (positions, risk, strategy state, analytics) are derived materializations from the event stream.
- Events are append-only. Corrections MUST be represented as compensating events and MUST NOT mutate previously written events.

### 2) Deterministic replay requirement

- Given the same ordered event stream and same code/config version set, replay MUST produce identical decisions and state projections.
- Decision functions MUST be pure with respect to replay inputs (no implicit wall-clock calls, ambient randomness, or hidden mutable global state).
- Any non-deterministic dependency MUST be converted into explicit input data captured in events/metadata.

### 3) Fail-safe behavior on uncertainty

When uncertainty is detected (missing lineage, ordering gaps, stale dependencies, schema incompatibility, unresolved reconciliation, or confidence below policy threshold), modules MUST transition to one of these fail-safe modes and record the reason:

- **halt:** Stop issuing new decisions/orders.
- **throttle:** Reduce decision/order rate and tighten exposure/risk limits.
- **flatten:** Attempt controlled exposure reduction toward flat risk.

Fail-safe mode selection policy MUST be explicit, testable, and versioned.

### 4) Mandatory lineage identifiers

Every relevant event and derived record MUST carry these identifiers:

- `trace_id`
- `decision_id`
- `order_id`
- `fill_id`

Rules:

- IDs MUST be stable across retries/replays where semantic identity is unchanged.
- Child artifacts MUST preserve ancestry links to upstream IDs.
- Missing required IDs is a contract violation and MUST trigger fail-safe behavior.

### 5) UTC timestamp policy

All persisted timestamps MUST be UTC (RFC 3339 / ISO 8601 with explicit `Z` or `+00:00`) and include:

- `event_time`: when the business event actually occurred.
- `ingest_time`: when the platform first accepted/recorded the event.
- `process_time`: when the module processed the event.

Rules:

- `event_time` MAY be earlier than `ingest_time`; this is expected for delayed delivery.
- `process_time` MUST be set for every processing attempt.
- Timezone-local timestamps without offset are disallowed.

## Consequences

### Positive

- Full auditability and explainability of decisions and state transitions.
- Reproducible incident analysis via deterministic replay.
- Predictable risk posture under data/infra uncertainty.
- Strong cross-module interoperability through consistent lineage and time semantics.

### Tradeoffs

- Higher implementation rigor for event design, lineage propagation, and replay harnesses.
- Additional storage and processing overhead from immutable event retention.
- Increased migration work for modules currently anchored to mutable state-first models.

## Acceptance criteria

A module is merge-eligible only if all criteria below are satisfied:

1. **Event-sourced truth**
   - Writes immutable events as primary record.
   - Uses compensating events for correction; no historical mutation path.
2. **Deterministic replay**
   - Provides replay test(s) proving identical outputs for repeated runs over identical inputs.
   - Captures all non-deterministic influences as explicit event/metadata inputs.
3. **Fail-safe controls**
   - Implements and documents `halt`, `throttle`, and `flatten` modes.
   - Emits structured fail-safe reason codes and triggering evidence.
4. **Lineage enforcement**
   - Validates presence and format of `trace_id`, `decision_id`, `order_id`, `fill_id`.
   - Preserves parent-child lineage links across module boundaries.
5. **UTC timestamp compliance**
   - Persists `event_time`, `ingest_time`, and `process_time` in UTC with explicit offset.
   - Rejects or normalizes non-compliant timestamp inputs.
6. **Observability**
   - Exposes metrics/logs for replay determinism checks, lineage validation failures, and fail-safe activations.

## Pre-merge checklist for downstream modules

- [ ] Event store writes are append-only; no update/delete path for historical events.
- [ ] Projection/state stores can be fully rebuilt from event history.
- [ ] Replay harness exists and passes determinism assertions on canonical fixtures.
- [ ] Random/time/environmental inputs are explicitly captured and replayed.
- [ ] Fail-safe policy maps uncertainty classes to `halt|throttle|flatten`.
- [ ] Runtime emits machine-readable fail-safe reason code + evidence.
- [ ] `trace_id`, `decision_id`, `order_id`, `fill_id` are required at boundaries.
- [ ] Lineage propagation verified through integration test(s).
- [ ] `event_time`, `ingest_time`, `process_time` stored in UTC with explicit offset.
- [ ] Timestamp validation rejects timezone-ambiguous formats.
- [ ] Dashboards/alerts include fail-safe activation counts and lineage violations.
- [ ] Runbook updated with recovery/replay steps for fail-safe incidents.

## Implementation quick-start (recommended order)

1. Define/upgrade canonical event schema with required IDs and UTC timestamps.
2. Enforce append-only writes and compensating-event correction paths.
3. Add lineage and timestamp validators at ingress and inter-module boundaries.
4. Implement fail-safe mode engine (`halt|throttle|flatten`) and reason taxonomy.
5. Build deterministic replay harness and golden-fixture tests.
6. Add observability, alerts, and runbook procedures.
7. Gate merges on the acceptance criteria and checklist in this ADR.

## Related documents

- `docs/architecture/deterministic-pipelines.md`
- `docs/runbooks/deterministic-pipeline-migration.md`
- `docs/runbooks/lineage-enforcement-rollout.md`
