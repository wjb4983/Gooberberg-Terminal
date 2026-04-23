# Connectivity test matrix and quality gates

## Scope

This document defines the lean but complete connectivity test strategy across topology, authentication, and fault conditions for desktop ↔ API control-plane communication.

### Matrix axes

- **Environment topology**
  - `localhost`: direct local API + WS endpoint.
  - `tailscale`: private-network endpoint over tailnet identity and ACLs.
  - `reverse-proxy`: TLS-terminated ingress/proxy path (including header forwarding and upgrade behavior).
- **Auth mode**
  - `none` (dev only, local smoke).
  - `bearer-jwt` (default control-plane auth).
  - `device-bound-token` (desktop-bound/session-bound token path).
- **Connectivity fault case family**
  - transport interruption (DNS failure, connection reset, packet loss burst).
  - auth failure (expired/invalid token, clock skew rejection).
  - proxy/TLS mismatch (bad cert chain, websocket upgrade blocked).
  - backpressure/queue health degradation (stale heartbeat, enqueue lag).

## Lean matrix design

To keep runtime and flake risk under control, each topology has:

1. **Critical-path smoke** (must run fast and deterministically).
2. **A small set of targeted fault injections** (2–4 highest-risk cases only).

| Topology | PR smoke (required) | Nightly fault injections (required for RC) |
|---|---|---|
| `localhost` | API auth handshake, WS connect, replay resume happy path | token expiry mid-session, queue stale heartbeat, forced WS reset |
| `tailscale` | API + WS handshake with tailnet address, diagnostics surface reachable peer status | ACL deny simulation, tailnet peer transient loss, reconnect storm dampening |
| `reverse-proxy` | HTTPS + WSS through proxy, forwarded auth headers intact | synthetic TLS chain failure, WS upgrade rejection, proxy 502 burst + recovery |

## Test layers

### 1) Unit tests (fast, pure logic)

**Target modules**
- transport policy selector functions (endpoint priority/fallback).
- circuit-breaker state transitions (`closed` → `open` → `half-open` → `closed`).
- auth header attachment and refresh trigger rules.

**Required assertions**
- policy chooses expected endpoint per topology/config flags.
- circuit opens on threshold, suppresses flood retries, and probes on cooldown.
- auth headers attach only on allowlisted hosts/protocols.
- token refresh path does not duplicate/overwrite concurrent in-flight auth state.

### 2) Integration tests (service contracts)

**Coverage**
- API contract tests for auth, diagnostics, and queue health endpoints.
- WS contract tests for connect/subscribe, message replay, and resume tokens.
- replay/resume semantics:
  - server returns stable cursor/token.
  - client resumes from last acknowledged sequence.
  - duplicate delivery is tolerated/idempotent at handler boundary.
- queue health behavior:
  - heartbeat freshness thresholds.
  - stale/lagged queue status escalation in diagnostics payload.

**Execution style**
- run in hermetic fixtures using synthetic backend/proxy/TLS components.
- fixed seeds and bounded timers to limit flakiness.

### 3) End-to-end tests (desktop workflows)

**Required journeys**
- onboarding flow: endpoint selection, auth completion, first successful sync.
- diagnostics visibility: transport mode, auth mode, queue health, last error signature.
- recovery actions: retry/connect actions clear degraded state and validate recovered session.

**Artifacts on failure**
- UI screenshot.
- desktop logs + API/proxy fixture logs.
- trace bundle containing reconnect/circuit timeline.

## CI profiles

### Fast PR lane

Purpose: block regressions quickly with deterministic checks.

Runs on pull requests and release branches:
- lint/static checks.
- unit suite.
- selected integration smoke (`localhost` + one representative proxy contract).

Target runtime: **<= 15 minutes**.

### Nightly full-matrix lane

Purpose: broad regression discovery without slowing PR flow.

Runs nightly and on-demand for release candidates:
- full topology matrix (`localhost`, `tailscale`, `reverse-proxy`).
- auth mode coverage per topology.
- fault-injection suites with synthetic TLS/proxy fixtures.
- E2E onboarding/diagnostics/recovery journeys.

Target runtime: **<= 90 minutes** with parallelized matrix shards.

### Failure artifact capture

All CI lanes must publish artifacts for failed jobs:
- structured logs (desktop/app/api/proxy).
- protocol traces (WS reconnect/replay timeline).
- screenshots for UI/E2E failures.

Retention recommendation:
- PR lane: 7 days.
- nightly/release-candidate lanes: 14 days.

## Quality gates

### Release-branch required pass criteria

For branch pattern `release/*`:
- fast PR lane must pass on every merge.
- latest nightly full-matrix run must be green for all three topologies.
- no unresolved `critical` or `high` connectivity regressions.
- replay/resume and queue-health integration contracts must pass in all required auth modes.

### Flake budget and quarantine policy

- suite-level flake budget: **<= 2%** rolling 14-day failure rate for non-product defects.
- test-level quarantine threshold: any test exceeding **3 flakes in 10 runs**.
- quarantined tests:
  - are removed from blocking lanes.
  - require an owner and fix ETA.
  - remain visible in nightly reports until reinstated.
- blocker exception: critical-path smoke tests are **not eligible** for long-lived quarantine.

## Estimate and ownership

- **Estimated effort:** 6–9 engineering days.
- **Owner profile:** QA automation engineer plus backend/frontend test maintainers.

Suggested breakdown:
1. Matrix doc + harness design: 1 day.
2. Unit + integration additions: 2–3 days.
3. E2E journeys + artifact plumbing: 2 days.
4. CI lane wiring + gate enforcement + stabilization: 1–3 days.

## Risks, dependencies, rollout, rollback

### Primary risk

- E2E topology tests become slow/flaky if over-scoped.

Mitigation:
- keep E2E assertions focused on user-visible outcomes.
- isolate heavy fault injections to nightly lane.
- enforce deterministic fixtures and explicit timeouts.

### Dependencies

- Phase 2 UX specs.
- Phase 3 replay/circuit implementation.
- Phase 5 observability hooks.

### Acceptance criteria

- green matrix for all three topologies on release candidate.
- documented and reproducible failure signatures.
- recovery verification included for each required topology.

### Rollout strategy

- progressive gate enforcement:
  1. advisory-only signals.
  2. required checks on `release/*` branch.
  3. optional expansion to default branch once stable.

### Rollback plan

- temporarily relax non-critical matrix lanes while preserving core smoke blockers.
- keep replay/resume + connectivity smoke as non-negotiable release blockers.
