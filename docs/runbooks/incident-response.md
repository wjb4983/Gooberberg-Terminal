# Incident response runbook

This runbook provides first-response and stabilization procedures for API, WebSocket, Redis, and Postgres incidents.

## 1) Severity and ownership

## Severity guide

- **SEV-1:** Control plane unavailable or incorrect execution/risk behavior affecting live operations.
- **SEV-2:** Partial degradation (e.g., WS instability, intermittent API failures, Redis issues with fallback active).
- **SEV-3:** Minor defects, documentation/observability gaps, or non-critical feature issues.

## Incident roles

- **Incident Commander (IC):** coordinates response and timeline.
- **Operations Lead:** performs deploy/infra actions.
- **Application Lead:** investigates API/WS/service behavior.
- **Communications Lead:** stakeholder updates and status page/channel comms.

## 2) Immediate triage checklist (first 15 minutes)

1. Declare severity and assign IC.
2. Freeze non-incident deploys/changes.
3. Capture scope:
   - affected endpoints/topics/services
   - first seen timestamp
   - user/region blast radius
4. Gather evidence:
   ```bash
   timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
   timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml logs --tail=300 api-control-plane redis postgres
   ```
5. Validate basic liveness:
   ```bash
   timeout 20s curl -kfsS https://<your-domain>/healthz
   timeout 20s curl -kfsS https://<your-domain>/api/v1/health -H "Authorization: Bearer <token>"
   ```
6. Start incident timeline document immediately.

## 3) Service-specific playbooks

### A) API incident playbook

Symptoms:

- elevated 5xx/4xx errors
- slow response times
- health endpoint failing

Actions:

1. Check auth misconfiguration (`GB_API_AUTH_TOKEN`, `GB_API_PREFIX`).
2. Inspect API logs for stack traces and dependency errors.
3. Verify deployment drift (image tag, env file, compose render).
4. If recent deploy suspected, rollback to prior known-good image.

Validation:

```bash
timeout 20s curl -kfsS https://<your-domain>/api/v1/health -H "Authorization: Bearer <token>"
```

### B) WebSocket incident playbook

Symptoms:

- clients cannot connect
- repeated reconnect loops
- missing topic events

Actions:

1. Verify proxy websocket upgrade configuration.
2. Confirm clients send `subscribe` with valid topics.
3. Check API logs for malformed JSON / unsupported action errors.
4. Validate heartbeat behavior (`ping`/`pong`) in client.
5. If needed, restart API service to clear stale connection state.

Validation:

- Connect to `/ws`, subscribe, and trigger known event (`POST /jobs`) to verify envelope delivery.

### C) Redis incident playbook

Symptoms:

- job state missing after API restart
- delayed or missing queue consumption
- portfolio snapshot stream stale

Actions:

1. Check Redis container health and restart count.
2. Confirm DSN (`GB_REDIS_DSN`) and network connectivity.
3. Validate persistence volume and disk pressure.
4. If Redis is down, acknowledge degraded mode: API may fallback to in-memory behavior.
5. Recover Redis, then verify queue/state operations and pub/sub feed.

Validation:

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml exec redis redis-cli ping
```

### D) Postgres incident playbook

Symptoms:

- startup dependency waits/failures
- data-read/write errors in components that require DB

Actions:

1. Verify container health and credentials.
2. Confirm `GB_POSTGRES_DSN` syntax and secrets.
3. Check disk capacity and WAL/storage pressure.
4. Restore from backup if corruption suspected.

Validation:

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml exec postgres pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-gooberberg}
```

## 4) Risk / execution authority incident handling

If incident involves unexpected approvals/rejections:

1. Immediately switch to safe mode (pause strategy starts if needed).
2. Review recent risk decisions:
   - `GET /api/v1/risk/decisions/recent`
3. Review overrides:
   - `GET /api/v1/risk/overrides`
4. Remove or correct problematic overrides.
5. Re-test one controlled strategy intent before resuming traffic.

## 5) Data handling incident handling

If data payload size or schema issues cause instability:

- Verify control-plane payloads remain JSON metadata only.
- Move heavy payloads to external Arrow/Parquet artifacts and ship `*_ref` pointers.
- Avoid adding large arrays/blobs to API/WS envelopes during hotfixes.

## 6) Containment and rollback strategy

- Prefer reversible, minimal-change mitigation.
- Roll back images/config before deep refactors during active incident.
- Preserve forensic data (logs, env diff, image digests).
- Keep comms cadence (e.g., every 15–30 minutes for SEV-1/2).

## 7) Exit criteria

Incident can be resolved when:

- API health and key user flows are stable.
- WS subscription and event delivery are verified.
- Redis/Postgres are healthy with expected durability behavior.
- Risk gating behavior confirmed with controlled test intents.
- Monitoring shows sustained recovery for agreed window.

## 8) Post-incident review checklist

Within 48 hours:

1. Produce timeline (trigger, detection, mitigation, recovery).
2. Document root cause and contributing factors.
3. Add CAPAs (corrective and preventive actions) with mandatory owner, due date, and verification evidence fields (use `docs/incidents/postmortem-template.md`).
4. Review open CAPAs weekly until closure, with escalation for overdue actions.
5. Track incident-class recurrence rate and compare against previous reporting window.
6. Update architecture/contracts/runbooks to capture new learnings.
