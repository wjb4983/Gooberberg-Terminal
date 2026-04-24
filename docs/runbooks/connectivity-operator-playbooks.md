# Connectivity operator playbooks

This document is the incident quick-index for connectivity regressions across localhost, Tailscale, and reverse-proxy topologies.

## 1) All offline

**Symptoms**
- Desktop/API/WS all report disconnected.
- Synthetic healthy-path checks fail for all topologies.

**Immediate actions**
1. Run topology synthetic smoke (`scripts/ops/run-connectivity-smoke-matrix.sh`).
2. Verify backend liveness (`/healthz`) from each topology ingress.
3. Confirm DNS/Tailscale/proxy reachability and cert status.
4. Freeze rollout and route incident via SEV process.

**Escalation**
- If all three topologies fail, treat as control-plane incident and page on-call.

## 2) WS stuck connecting

**Symptoms**
- UI stays in `connecting`/`reconnecting`.
- WS connect/disconnect loops and replay not completing.

**Immediate actions**
1. Validate WS endpoint is reachable through current topology.
2. Inspect WS upgrade/header forwarding (especially reverse proxy).
3. Confirm reconnect backoff is active (avoid rapid-loop reconnect).
4. Validate replay cursor behavior (`replay_complete` or explicit replay error event).

**Escalation**
- If reconnect storm impacts user workflows, enable degraded-mode fallback and page app owner.

## 3) Auth rejected

**Symptoms**
- Protected routes return `401/403` while health endpoints stay green.
- Synthetic bad-token check behavior unexpectedly changes.

**Immediate actions**
1. Verify token source and expected scope for the current environment.
2. Check token expiry/revocation and clock skew.
3. Confirm reverse proxy preserves `Authorization` header.
4. Rotate token or refresh desktop auth session.

**Escalation**
- Multiple tenants/operators affected: escalate to security + platform on-call.

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

- `docs/runbooks/desktop-cannot-connect.md`
- `docs/runbooks/ws-reconnect-storm.md`
- `docs/runbooks/auth-token-rejected.md`
- `docs/runbooks/queue-heartbeat-stale.md`
- `docs/runbooks/tailscale-connectivity.md`
