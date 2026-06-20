# runbooks

- `local-dev.md`: Local environment setup, validation flow, and troubleshooting.
- `server-deploy.md`: Production Docker Compose deployment and operations steps.
- `local-server-browser.md`: Local backend/frontend ports, browser access, and VS Code port-forward troubleshooting.
- `incident-response.md`: Incident severity, triage, mitigation, and recovery playbooks.
- `release-process.md`: Versioning policy and scripted release flow.
- `slo-and-latency-objectives.md`: SLO definitions for event loss, audit latency, decision-loop budget, and MTTA/MTTR.
- `safe-restart.md`: Ordered low-risk restart procedure with validation and rollback criteria.
- `backfill-and-replay-verification.md`: Backfill workflow and deterministic replay parity validation.
- `auth-token-rejected.md`: Diagnose and fix auth token validation failures.
- `ws-reconnect-storm.md`: Investigate and stabilize repeated WebSocket reconnect loops.
- `queue-heartbeat-stale.md`: Recover queue heartbeat freshness and worker liveness.
- `connectivity-operator-playbooks.md`: Quick incident playbooks for all offline, WS stuck connecting, auth rejected, and queue stale scenarios.

## Start here: exact order for common operations

If you are new, follow only one path below at a time.

1. **First-time setup:** `../../scripts/README.md` → section **A) First-time setup**.
2. **After pulling updates:** `../../scripts/README.md` → section **B) After git pull**.
3. **Server restart (no updates):** `../../scripts/README.md` → section **C) Routine restart**.

After each path, use `local-server-browser.md` to verify local browser and VS Code port-forward access.
