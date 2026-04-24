# ADR: WS + HTTP Connectivity Contract

- **Status:** Proposed
- **Date:** 2026-04-24
- **Owners:** Platform + Control-plane teams
- **Decision scope:** Canonical health, auth, and websocket resume semantics for API control-plane connectivity.

## Context

Control-plane connectivity needed a single contract that both backend and clients can implement consistently:

- Health endpoints had drifted in purpose and caller expectations.
- WebSocket reconnect needed deterministic resume behavior for short disconnects.
- Connection lifecycle diagnostics were inconsistent.
- Auth behavior needed explicit endpoint-level rules.

## Decision

### 1) Canonical health endpoint contract

| Endpoint | Method | Auth | Contract |
|---|---|---|---|
| `/healthz` | GET | Public | Liveness only: returns process up signal for infra probes. |
| `/api/v1/health` | GET | Public | Service + dependency summary (service metadata plus dependency configured/reachability shape). |
| `/api/v1/health/queue` | GET | Public | Queue depth + worker heartbeat freshness signal (`ok` / `degraded`). |

#### Status payload expectations

- `/healthz` returns `{ "status": "ok" }` on healthy process.
- `/api/v1/health` returns:
  - `service`, `version`, `status`
  - `postgres` and `redis` objects with `configured`, `reachable`, `detail`
- `/api/v1/health/queue` returns:
  - `status`, `queue_depth`
  - `worker_heartbeat_at`, `worker_heartbeat_age_seconds`
  - `detail`

### 2) WebSocket resume contract (`/ws`)

#### Resume input

- Clients may pass `last_seq=<n>` query parameter on `/ws` reconnect.
- `last_seq` must be a non-negative integer.

#### Replay behavior

- Server retains a bounded event buffer (`GB_WS_REPLAY_WINDOW`) with globally monotonic `seq`.
- On first `subscribe` after connect, if replay is enabled:
  - Server replays matching topic events where `seq > last_seq`.
  - Server sends `replay_complete` with replay counts/bounds when done.
- If cursor is outside retained window:
  - Server sends explicit `replay_required` event with `requested_last_seq`, `oldest_available_seq`, `latest_available_seq`.
- If cursor is malformed:
  - Server sends explicit `replay_cursor_invalid` event.

#### Feature flag

- Replay path is gated by `GB_WS_REPLAY_ENABLED`.
- If disabled and `last_seq` is supplied, server emits `replay_disabled` and proceeds with live-only behavior.

### 3) Connection diagnostics contract

Control-plane emits structured log events for websocket and auth diagnostics:

- `ws_connect`
- `ws_disconnect`
- `ws_subscribe`
- `ws_unsubscribe`
- `ws_replay` outcomes (`ok`, `too_old`, `invalid`, `disabled`)
- `auth_failure` (token mismatch / insufficient scope)

Diagnostic fields include `connection_id`, `client`, and replay bounds where applicable.

### 4) Auth contract

When `GB_API_AUTH_TOKEN` is configured:

- **Public endpoints** (no bearer required):
  - `/healthz`
  - `/api/v1/health`
  - `/api/v1/health/queue`
  - `/api/v1/health/queue/heartbeat`
- **All other HTTP endpoints** require `Authorization: Bearer <token>` and scope checks.

## Rollout

- Default replay enabled in non-prod verification environments.
- Canary rollout to internal users first.
- Monitor replay diagnostics (`ws_replay`) and auth failures.

## Rollback

- Set `GB_WS_REPLAY_ENABLED=false` to disable replay path and retain baseline reconnect behavior.
- Keep existing WS connection + subscribe flow unchanged.

## Acceptance criteria mapping

- Replay works for short disconnects via bounded buffer and `last_seq` resume.
- Too-old cursor produces deterministic explicit replay-required payload.
- Connectivity endpoints return predictable status/error payloads.
- Contract documented in this ADR for approval.
