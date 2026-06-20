# Tauri ↔ Backend Connectivity Baseline Audit

## Scope

This baseline captures the current transport contract between the desktop Tauri client and the API control-plane backend, focused on HTTP, auth, health checks, and WebSocket behavior.

## Audit Table

| Area | Entry points / modules | Observed baseline behavior | Evidence |
|---|---|---|---|
| Client transport entry points | `apps/desktop-tauri/src/api/client.ts`; `libs/ts/@gb/api-client/src/index.ts` | Desktop client creates `GbApiClient` without an auth header provider for local-only mode. Shared client uses `requestJson()` for all HTTP calls, has reconnecting topic WS support, and appends `last_seq` query parameter during reconnect attempts. | `createDesktopApiClient`; `GbApiClient.requestJson`; `connectTopicWebSocket`; `withResumeSeq`. |
| Auth behavior | `apps/api-control-plane/app/core/auth.py`; `apps/desktop-tauri/src/settings/tokenStorage.ts`; `apps/desktop-tauri/src-tauri/src/main.rs` | Backend middleware validates one static bearer token (`GB_API_AUTH_TOKEN`), sets request scope, and bypasses configured health paths. The local-only desktop/browser frontend no longer stores API bearer tokens or injects Authorization headers. No token rotation or expiry lifecycle logic is present in the local-only client. | `BearerTokenAuthMiddleware.dispatch`; config `env_prefix="GB_"` + `api_auth_token`; local-only client request wrappers. |
| Health endpoints | `apps/api-control-plane/app/main.py`; `apps/api-control-plane/app/api/routers/health.py` | `/healthz`, `/api/v1/health`, `/api/v1/health/queue`, and `/api/v1/health/queue/heartbeat` are included in middleware auth bypass. Health response marks Postgres/Redis reachability as placeholder (`reachable=None`) with explicit “not implemented” detail text. | `app.add_middleware(...health_paths={...})`; `@app.get('/healthz')`; health router response builders. |
| WS behavior and limitations | `apps/api-control-plane/app/api/routers/ws.py`; `apps/api-control-plane/app/ws/manager.py`; `apps/desktop-tauri/src/hooks/useResumableTopicStream.ts` | WS endpoint accepts connection, ping/pong and subscribe/unsubscribe; publishes sequenced events in-memory (`_seq`) to current subscribers only. Desktop hook tracks `lastSeq` and passes it back through reconnect query via API client, but backend `/ws` does not read or replay from `last_seq`, so missed events are not backfilled. Hook falls back to polling when not connected. | WS router message loop lacks query-param handling/replay path; manager only broadcasts to active subscribed sockets; hook sets `lastSeqRef` and provides `getResumeSeq`. |

## Explicit Findings

1. **`/healthz` + `/api/v1/health*` are intentionally unauthenticated.**
   - Auth middleware bypasses explicit health path set including `/healthz`, `/api/v1/health`, `/api/v1/health/queue`, and `/api/v1/health/queue/heartbeat`.

2. **Token model is static bearer (`GB_API_AUTH_TOKEN`) with no rotation/expiry lifecycle.**
   - Backend compares incoming `Authorization` header against one configured static bearer token.
   - No TTL, refresh token, issuance, revocation list, or expiry checks are implemented in current auth path.

3. **Client adds `last_seq` on reconnect but backend `/ws` does not use it for replay.**
   - Shared API client appends `last_seq` to the WS URL when resume sequence is known.
   - Server-side websocket handler ignores query params and only processes inbound text frames for subscribe/unsubscribe/ping.
   - Connection manager has monotonic in-memory sequence generation but no persisted replay buffer.

4. **No explicit HTTP timeout/abort policy in `GbApiClient.requestJson`.**
   - `requestJson` calls `fetchImpl` directly and does not set `AbortSignal`, timeout wrapper, or retry policy.

5. **Health checks include placeholders for Redis/Postgres reachability.**
   - Health response sets `reachable=None` for both dependencies with placeholder detail indicating checks are not implemented.

## Estimate and Ownership

- **Estimated implementation effort:** 2–3 engineering days.
- **Owner profile:** Staff full-stack engineer with FastAPI + React/Tauri familiarity.

## Risks

- Audit may miss hidden transport call sites if current path inventory is incomplete.

## Dependencies

- Access to all app router modules and shared API client modules across desktop and backend repositories.

## Acceptance Criteria

- Baseline doc and ADR are reviewed and signed off with no `TBD` sections.
- Every material claim traces back to concrete file paths and implementation points.

## Rollout Strategy

- Review in architecture sync.
- Freeze transport-contract changes until ADR approval.

## Rollback Plan

- If design disagreement blocks adoption, keep ADR status as draft and continue only non-breaking instrumentation work.
