# Runbook: Desktop cannot connect

## When to use

Use this playbook when desktop users report inability to reach backend APIs or WS streams.

## Signals

- Desktop shows disconnected/offline state.
- Synthetic connectivity check fails for localhost, tailnet, or reverse-proxy lane.
- Increase in `api_liveness_success_rate` errors or WS connection failures.

## Triage checklist

1. Identify affected environment (`local`, `staging`, `prod`).
2. Confirm base URL, path prefix, and token config from desktop diagnostics.
3. Validate health, auth, then WS in that order.

## Commands (triage)

> Replace placeholders (`$BASE_URL`, `$TOKEN`) before execution.

```bash
timeout 10s curl -fsS "$BASE_URL/healthz"
```
Expected output: JSON body containing service health status and HTTP 200.

```bash
timeout 10s curl -i -fsS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/health"
```
Expected output: HTTP 200 for valid token; if this endpoint is bypassed in env, note exception and run next auth-protected check.

```bash
timeout 10s curl -i -fsS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/positions"
```
Expected output: HTTP 200 from auth-protected endpoint.

```bash
timeout 20s curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" "$BASE_URL/ws"
```
Expected output: HTTP 101 upgrade (when raw curl upgrade path is supported by env).

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml ps
```
Expected output: API and required dependencies in `Up` state.

## Decision tree

- **Health fails:** likely infra/process/network outage; escalate to platform immediately.
- **Health passes, auth fails:** follow `auth-token-rejected.md`.
- **Health + auth pass, WS fails/reconnect loops:** follow `ws-reconnect-storm.md`.
- **Only reverse-proxy lane fails:** validate path rewrite and base URL prefix config.

## Mitigation

- Correct base URL/path prefix in desktop config.
- Restart unhealthy backend components.
- Temporarily disable WS-dependent UI streams and fall back to polling (if supported) while issue is mitigated.

## Escalation

Escalate to SRE/platform when:

- Two or more lanes fail simultaneously.
- Health endpoint is failing for >5 minutes.
- TLS or reverse-proxy misrouting is suspected.
