# ADR: Transport Contract v1

- **Status:** Proposed
- **Date:** 2026-04-23
- **Owners:** Platform + Desktop teams
- **Decision scope:** Canonical HTTP/WS transport semantics between desktop clients and API control-plane.

## Context

Current transport behavior works but is only partially explicit:

- Health endpoints are intentionally unauthenticated.
- Auth is static bearer-token based.
- WS reconnect sends `last_seq` but server replay is not implemented.
- HTTP request timeout/abort policy is not standardized.
- Health dependency probes expose placeholder reachability.

A shared contract is needed so client UX and backend reliability behavior remain aligned as implementations evolve.

## Decision

### 1) Canonical Transport States

All clients should normalize transport status into the following canonical states:

- **`online`**
  - Authenticated HTTP calls succeed within timeout budget.
  - WS is connected (if configured) and receiving events within expected lag budget.
- **`degraded`**
  - Core API is reachable, but one or more subsystem signals is unhealthy (e.g., queue health degraded, dependency probe degraded, fallback polling active).
- **`offline`**
  - API endpoint is unreachable (DNS/TCP/network failure) or repeated timeout budget exhaustion.
- **`auth_failed`**
  - API responds with 401/403 due to missing/invalid credentials.
- **`ws_lagging`**
  - WS connection is established but event freshness/sequence continuity is behind acceptable threshold (gap/lag condition), requiring catch-up strategy.

### 2) Canonical Endpoint + Auth Map

| Endpoint | Method(s) | Auth expectation | Purpose |
|---|---|---|---|
| `/healthz` | GET | Unauthenticated | Liveness probe suitable for infra/load balancer checks. |
| `/api/v1/health` | GET | Unauthenticated | Service health summary including dependency configuration/reachability status. |
| `/api/v1/health/queue` | GET | Unauthenticated | Queue and worker-heartbeat health status. |
| `/api/v1/health/queue/heartbeat` | POST | Unauthenticated (current baseline) | Worker heartbeat update endpoint used by queue workers. |
| `/api/v1/**` (non-health) | all | Bearer required | Control-plane application APIs. |
| `/ws` | WebSocket | Align with backend policy (currently no explicit token validation in handler) | Realtime subscriptions (`subscribe`/`unsubscribe`) and event stream delivery. |

**Auth contract v1:**

- Backend validates static bearer token value from `GB_API_AUTH_TOKEN` for protected HTTP endpoints.
- Health/liveness endpoints remain unauthenticated by explicit allowlist.
- WS auth hardening (token validation, consistent scope checks) is a follow-up item and should not silently diverge from HTTP policy.

### 3) Replay + Event Ordering Contract

#### Ordering

- WS events are **globally monotonic by `seq`** as emitted by backend event manager.
- Clients must treat `seq` as ordering metadata and preserve in-memory high-water mark (`last_seq`).

#### Replay requirements

- If client reconnects with `last_seq=N`, backend **must** either:
  1. Replay all durable events with `seq > N` for subscribed topics in order, then continue live stream, **or**
  2. Return an explicit non-replayable signal so client can initiate deterministic snapshot + resume flow.

- Silent ignore of replay cursor is non-compliant once v1 transport contract is approved.

#### Gap handling

- Client detecting sequence discontinuity should transition to `ws_lagging`.
- Recovery path: trigger snapshot/poll backfill for affected domain, then resume WS from new high-water mark.

#### Durability assumptions

- Replay-capable implementations require bounded durable event retention (in-memory ring buffer or persistent store) and topic-aware filtering.
- Replay window SLA should be documented (e.g., minimum event count or time retention).

## Consequences

### Positive

- Shared client UX semantics for network/auth/realtime states.
- Predictable recovery from reconnect and event gaps.
- Clear auth and endpoint expectations for operations and security reviews.

### Trade-offs

- Requires implementation work for replay support and timeout standards.
- Potential short-term freeze on transport-affecting changes until contract ratified.

## Implementation Plan (Initial)

1. Add standardized HTTP timeout + abort policy in shared API client.
2. Define WS auth policy parity with HTTP endpoints.
3. Implement replay-capable WS path honoring `last_seq`.
4. Add explicit lag/gap detection and canonical state mapping in desktop transport hooks.
5. Upgrade health dependency checks from placeholders to active probes where feasible.

## Estimate and Ownership

- **Estimated effort:** 2–3 engineering days.
- **Recommended owner profile:** Staff full-stack engineer experienced with FastAPI and React/Tauri transport layers.

## Status Notes

- If architecture review blocks agreement, keep this ADR in draft/proposed state and proceed only with non-breaking instrumentation tasks.
