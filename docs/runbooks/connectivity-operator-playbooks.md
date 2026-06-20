# Connectivity operator playbooks

This document is the incident quick-index for local connectivity regressions.

## 1) All offline

**Symptoms**
- Browser/API/WS all report disconnected.
- Local synthetic healthy-path checks fail.

**Immediate actions**
1. Run local synthetic smoke (`scripts/ops/connectivity-synthetic-check.sh`).
2. Verify backend liveness (`/healthz`) on `http://127.0.0.1:8000`.
3. Verify the frontend dev server on `http://127.0.0.1:1420` or the VS Code forwarded port.
4. Freeze rollout and route incident via SEV process if the local stack cannot recover.

**Escalation**
- If local backend health and browser access both fail after restart, treat as a control-plane incident and page on-call.

## 2) WS stuck connecting

**Symptoms**
- UI stays in `connecting`/`reconnecting`.
- WS connect/disconnect loops and replay not completing.

**Immediate actions**
1. Validate `ws://127.0.0.1:8000/ws` is reachable from the local runtime context.
2. Confirm reconnect backoff is active (avoid rapid-loop reconnect).
3. Validate replay cursor behavior (`replay_complete` or explicit replay error event).

**Escalation**
- If reconnect storm impacts user workflows, enable degraded-mode fallback and page app owner.

## 3) Auth rejected

**Symptoms**
- Protected routes return `401/403` while health endpoints stay green.
- Synthetic bad-token check behavior unexpectedly changes.

**Immediate actions**
1. Verify token source and expected scope for the current local environment.
2. Check token expiry/revocation and clock skew.
3. Rotate token or refresh the local auth session.

**Escalation**
- Multiple operators affected: escalate to security + platform on-call.

## 4) Queue stale

**Symptoms**
- `/api/v1/health/queue` returns stale/degraded.
- Diagnostics surface delayed or stale worker heartbeat.

**Immediate actions**
1. Confirm queue backend connectivity and credentials.
2. Verify worker heartbeat emission frequency.
3. Restart stuck workers and monitor heartbeat freshness recovery.
4. Keep API available; degrade queue-dependent actions if necessary.

**Escalation**
- If stale state persists beyond SLO window, treat as reliability incident and page queue owners.

## Related detailed runbooks

- `docs/runbooks/local-server-browser.md`
- `docs/runbooks/ws-reconnect-storm.md`
- `docs/runbooks/auth-token-rejected.md`
- `docs/runbooks/queue-heartbeat-stale.md`
