# Connectivity matrix, layered tests, and release gates

## Scope and intent

This plan defines how we verify desktop connectivity for three deployment topologies and five core failure/behavior cases while keeping pull-request feedback fast.

- **Topologies:** `localhost`, `tailscale`, `reverse-proxy`
- **Core cases:** healthy path, bad token, backend down, stale queue heartbeat, WS disconnect/resume
- **Owner profile:** QA automation + SRE
- **Estimate:** 4–6 days
- **Dependencies:** Phases 1–4

## Topology × case matrix

| Topology | Healthy path | Bad token | Backend down | Stale queue heartbeat | WS disconnect/resume |
|---|---|---|---|---|---|
| `localhost` | Required smoke | Required smoke | Required smoke | Nightly full matrix | Required smoke |
| `tailscale` | Required smoke | Required smoke | Required smoke | Nightly full matrix | Required smoke |
| `reverse-proxy` | Required smoke | Required smoke | Required smoke | Nightly full matrix | Required smoke |

### Case definitions (pass/fail contracts)

1. **Healthy path**
   - `/healthz` returns `200`.
   - `/api/v1/health` returns `status=ok` or `status=degraded` with non-fatal dependencies.
   - WS endpoint accepts connection/subscription handshake.
2. **Bad token**
   - Auth-protected route returns `401` or `403` with structured auth failure payload.
3. **Backend down**
   - Connectivity check times out quickly and surfaces deterministic failure code (`timeout`, `connect_error`, or `upstream_unavailable`).
4. **Stale queue heartbeat**
   - Queue endpoint marks stale/degraded and diagnostics reflect stale worker heartbeat.
5. **WS disconnect/resume**
   - Reconnect proceeds with backoff/circuit policy and replay cursor semantics (`replay_complete`, `replay_required`, or `replay_disabled`) are explicit.

## Layered test implementation

### 1) Unit layer (fast logic)

Focus: retry/timeout/circuit transitions.

- Validate transition behavior around repeated failures and cooldown probe windows.
- Validate timeout classification remains deterministic.
- Validate retry gating avoids reconnect storms.

Execution target:
- Fast suite (`<5 min`) in PR lane.

### 2) Integration layer (contracts)

Focus: health/auth/ws/replay contracts.

- Health contracts: `/healthz`, `/api/v1/health`, `/api/v1/health/queue`
- Auth contracts: missing/invalid/revoked token paths
- WS contracts: subscribe ack, invalid cursor, replay/resume outcomes
- Queue freshness contracts: heartbeat recency surfaces degraded state when stale

Execution target:
- Smoke subset in PR lane
- Full contract coverage in nightly matrix

### 3) E2E layer (operator journeys)

Focus: onboarding + diagnostics + recovery actions.

- Onboarding path reaches connected state for chosen topology.
- Diagnostics surface transport/auth/queue/WS status.
- Recovery actions verify retry/reconnect and updated healthy status.

Execution target:
- Nightly matrix only (plus on-demand RC runs)

## Synthetic checks and alerting

Synthetic checks run per topology and publish machine-readable results:

- `healthy_path`
- `bad_token`
- `backend_down`
- `queue_stale`
- `ws_resume`

Alert policy:

- Page on **smoke regression** in any topology for two consecutive runs.
- Open advisory ticket on first failure for non-blocking nightly-only scenarios.
- Track 7-day moving failure rate; escalate when >2% for smoke checks.

## Operator playbooks

Primary operator playbooks are consolidated in:

- `docs/runbooks/connectivity-operator-playbooks.md`

Required scenarios:

- All offline
- WS stuck connecting
- Auth rejected
- Queue stale

## Release gate policy

### Required gate for release candidates

A release candidate **cannot ship** unless connectivity smoke passes in all three topologies:

- `localhost`
- `tailscale`
- `reverse-proxy`

### CI scheduling model

- **PR checks:** keep fast/unclunky; run lint + unit + integration smoke representative set.
- **Nightly only:** full matrix (all topologies, extended scenarios, E2E).

### Rollout strategy

1. **Advisory gate first** (this release): failures notify but do not hard-block.
2. **Mandatory gate next release**: required check blocks RC ship.

### Rollback strategy

If extended nightly scenarios are flaky:

- Keep core connectivity smoke required.
- Temporarily downgrade flaky extended scenarios to advisory.
- Re-promote once stabilized.

## Acceptance criteria

- RC gate enforces smoke pass across all three target topologies.
- Nightly full matrix executes all listed layered suites and synthetic checks.
- Operator playbooks exist for all four named incident scenarios.
