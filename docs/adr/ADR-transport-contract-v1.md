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

### 2) HTTP transport policy contract

- **Default timeout classes**
  - `interactive`: 10s default (`GB_HTTP_DEFAULT_TIMEOUT_MS` in desktop env, overridable per request).
  - `heavy_read`: 30s default for large/expensive reads.
- **Retry policy**
  - Never retry on `401`, `403`, `422`.
  - Retry only bounded attempts with jitter on `5xx` and transient network errors.
- **Idempotency guardrails**
  - Automatic retries for `GET`/`HEAD`.
  - Retries for `POST` only on approved idempotent endpoint list.
  - Non-idempotent writes remain single-attempt unless explicitly opted in.

### 3) Canonical Endpoint + Auth Map

| Endpoint | Method(s) | Auth expectation | Purpose |
|---|---|---|---|
| `/healthz` | GET | Unauthenticated | Liveness probe suitable for infra/load balancer checks. |
| `/api/v1/health` | GET | Unauthenticated | Service health summary including dependency configuration/reachability status. |
| `/api/v1/health/queue` | GET | Unauthenticated | Queue and worker-heartbeat health status. |
| `/api/v1/health/queue/heartbeat` | POST | Unauthenticated (current baseline) | Worker heartbeat update endpoint used by queue workers. |
| `/api/v1/**` (non-health) | all | Bearer required | Control-plane application APIs. |
| `/ws` | WebSocket | Align with backend policy (currently no explicit token validation in handler) | Realtime subscriptions (`subscribe`/`unsubscribe`) and event stream delivery. |

### 4) Replay + Event Ordering Contract

#### Ordering

- WS events are **globally monotonic by `seq`** as emitted by backend event manager.
- Clients must treat `seq` as ordering metadata and preserve in-memory high-water mark (`last_seq`).

#### Replay requirements

- If client reconnects with `last_seq=N`, backend **must** either:
  1. Replay all retained events with `seq > N` for subscribed topics in order, then continue live stream, **or**
  2. Return explicit replay-required metadata so client can initiate deterministic snapshot + resume flow.

#### Window contract

- `GB_WS_REPLAY_WINDOW` controls max retained events for in-process replay.
- If `last_seq` is older than the earliest retained event, backend sends `replay_required` with bounds (`oldest_available_seq`, `latest_available_seq`).

#### Gap handling

- Client detecting sequence discontinuity should transition to `ws_lagging`.
- Recovery path: trigger snapshot/poll backfill for affected domain, reset high-water mark, then resume WS.

## Operational toggles

- `GB_WS_REPLAY_WINDOW` (backend) — replay buffer depth for WS resume.
- `GB_HTTP_DEFAULT_TIMEOUT_MS` (desktop env via `VITE_GB_HTTP_DEFAULT_TIMEOUT_MS`) — default HTTP timeout baseline.
- `VITE_GB_WS_RECONNECT_MIN_MS` / `VITE_GB_WS_RECONNECT_MAX_MS` — reconnect bounds.

## Risks

- Replay buffer memory/cost tradeoffs.
- Event ordering and replay consistency bugs under burst load.

## Dependencies

- Phase 1 ADR ratification.
- Phase 2 diagnostic UX for operator visibility.

## Acceptance criteria

- Deterministic behavior under injected latency, disconnect, and packet loss simulation.
- No duplicate side-effects for retried non-idempotent operations.

## Rollout strategy

- Canary to internal operators first.
- Enable replay + circuit logic per environment flag.

## Rollback plan

- Disable replay/circuit enforcement flags.
- Revert to current reconnect + polling fallback behavior.

## Estimate and Ownership

- **Estimated effort:** 6–8 engineering days.
- **Recommended owner profile:** Senior backend engineer + frontend platform engineer.
