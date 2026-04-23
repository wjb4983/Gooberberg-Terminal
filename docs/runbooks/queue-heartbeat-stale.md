# Runbook: Queue heartbeat stale

## When to use

Use when queue heartbeat endpoint indicates stale workers or synthetic queue heartbeat checks fail.

## Signals

- `/api/v1/health/queue/heartbeat` reports stale/missing heartbeat.
- Alerts for queue health or processing lag increase.

## Triage commands

```bash
timeout 10s curl -i -sS "$BASE_URL/api/v1/health/queue/heartbeat"
```
Expected output: HTTP 200 with heartbeat timestamp newer than stale threshold.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml ps
```
Expected output: queue/worker components are `Up`.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 worker-training worker-research
```
Expected output: ongoing heartbeat/update logs without repeated connection errors.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 redis
```
Expected output: no persistent connection/auth failures.

## Diagnostics focus

1. Determine whether stale heartbeat is producer-side (worker not sending) or store-side (write path broken).
2. Verify queue backend reachability and auth.
3. Check recent deploys affecting heartbeat emission frequency.
4. Validate alert threshold vs expected idle periods.

## Mitigation

- Restart affected worker process.
- Restore queue backend connectivity/credentials.
- Temporarily widen stale threshold only if workload pattern justifies it and incident commander approves.

## Escalation

Escalate to backend + platform if heartbeat remains stale for >10 minutes after worker restart.
