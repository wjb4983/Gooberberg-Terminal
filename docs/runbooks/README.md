# runbooks

- `local-dev.md`: Local environment setup, validation flow, and troubleshooting.
- `server-deploy.md`: Production Docker Compose deployment and operations steps.
- `tailscale-connectivity.md`: Tailnet exposure, client validation, and connectivity troubleshooting.
- `incident-response.md`: Incident severity, triage, mitigation, and recovery playbooks.
- `release-process.md`: Versioning policy and scripted release flow.

## Start here: exact order for common operations

If you are new, follow only one path below at a time.

1. **First-time setup:** `../../scripts/README.md` → section **A) First-time setup**.
2. **After pulling updates:** `../../scripts/README.md` → section **B) After git pull**.
3. **Server restart (no updates):** `../../scripts/README.md` → section **C) Routine restart**.

After each path, use `tailscale-connectivity.md` to verify connectivity from another machine on the same tailnet.
