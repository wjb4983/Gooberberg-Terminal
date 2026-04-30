# Safe restart runbook

Use this runbook to restart services without violating durability or decision-loop objectives.

## Preconditions

1. Confirm no active SEV-1 incident.
2. Freeze deploys and risky config edits during restart window.
3. Confirm queue heartbeat freshness and backlog depth are within normal ranges.
4. Capture current health and version metadata.

```bash
timeout 30s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml ps
timeout 20s curl -kfsS https://<your-domain>/healthz
timeout 20s curl -kfsS https://<your-domain>/api/v1/health -H "Authorization: Bearer <token>"
```

## Restart procedure (recommended order)

1. **Pause intake (if supported):** temporarily disable new strategy starts or enqueue operations.
2. **Restart stateless edge first:** API/control-plane processes.
3. **Restart workers second:** job consumers, execution or background services.
4. **Restart stateful dependencies only when required:** Redis/Postgres in controlled order.
5. **Resume intake** after post-restart validation.

Example:

```bash
timeout 60s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml restart api-control-plane
timeout 60s docker compose --env-file config/env/.env -f infra/compose/docker-compose.prod.yml restart worker-training service-risk-exec
```

## Post-restart validation

1. API and WS health checks pass.
2. Audit API p95 latency remains within SLO alert threshold.
3. Event throughput stable; no sustained event loss signals.
4. Decision loop p95 latency under 1,500 ms.

```bash
timeout 20s curl -kfsS https://<your-domain>/api/v1/health -H "Authorization: Bearer <token>"
timeout 20s curl -kfsS https://<your-domain>/api/v1/risk/decisions/recent -H "Authorization: Bearer <token>"
```

## Rollback criteria

Rollback to previous image/version when any condition holds for > 10 minutes:

- audit API error rate > 1%
- end-to-end decision latency p99 > 3,000 ms
- replay parity canary fails
- elevated event loss beyond short-window thresholds
