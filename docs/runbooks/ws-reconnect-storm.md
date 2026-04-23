# Runbook: WS reconnect storm

## When to use

Use this playbook when clients repeatedly reconnect to WS, causing noisy alerts or degraded stream reliability.

## Signals

- Increased `ws_reconnect_attempts_total` and `ws_reconnect_loop_detected_total`.
- Degraded `ws_session_stability` SLI.
- User-reported live data flicker/staleness.

## Triage commands

```bash
timeout 10s curl -i -sS "$BASE_URL/healthz"
```
Expected output: HTTP 200. If failing, handle as general connectivity outage first.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=300 api-control-plane
```
Expected output: WS connect/disconnect reason logs, close codes, reconnect attempt counters.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=300 nginx
```
Expected output: stable upstream responses for `/ws`; no recurring 502/504 bursts.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml top
```
Expected output: API process not thrashing or OOM-killed.

## Diagnostics focus

1. Inspect WS close codes and reason classes (network reset, server close, idle timeout).
2. Check heartbeat cadence and timeout thresholds for false positives.
3. Validate reconnect backoff/jitter behavior in client.
4. Compare reconnect storm timing against deploy/config changes.
5. Quantify replay-gap rate during storm.

## Mitigation

- Increase reconnect backoff/jitter to reduce thundering herd.
- Relax overly aggressive idle timeout/heartbeat thresholds.
- Roll back recent proxy or WS route changes if correlation is strong.
- Temporarily demote storm alert from paging if caused by known transient network event.

## Escalation

Escalate to SRE + backend if stability remains below SLO for >15 minutes after mitigations.
