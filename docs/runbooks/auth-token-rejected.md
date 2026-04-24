# Runbook: Auth token rejected

## When to use

Use this playbook when backend returns 401/403 for expected valid clients, or auth synthetic checks regress.

## Signals

- Spikes in `auth_failures_total{reason="invalid_token"}`.
- Desktop diagnostics show repeated token rejection.
- Auth-protected synthetic check fails while health endpoint remains healthy.

## Triage commands

```bash
timeout 10s curl -i -sS "$BASE_URL/healthz"
```
Expected output: HTTP 200 confirms service liveness.

```bash
timeout 10s curl -i -sS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/positions"
```
Expected output: HTTP 200 for valid token.

```bash
timeout 10s curl -i -sS -H "Authorization: Bearer invalid-token" "$BASE_URL/api/v1/positions"
```
Expected output: HTTP 401 with explicit auth error classification.

```bash
timeout 20s docker compose -f infra/compose/docker-compose.dev.yml logs --tail=200 api-control-plane
```
Expected output: structured auth log entries with `auth_result` and `request_id`.

## Diagnostics focus

1. Verify configured token source (secret store/env var) matches expected active value.
2. Confirm no whitespace/encoding issues in injected `Authorization` header.
3. Validate auth classification (`missing_header` vs `invalid_token` vs `expired_token`).
4. Check revocation set alignment (`GB_API_AUTH_REVOKED_TOKEN_IDS`) when a previously valid token suddenly fails.
5. Correlate desktop `event_id` with backend `request_id` to isolate mismatch path.

## Mitigation

- Rotate/redeploy correct token secret.
- If rotating, run dual-accept window by adding new `GB_API_AUTH_TOKENS` record before removing old token.
- Patch client header injection bug if token not attached.
- If classification bug exists, keep 401 behavior and hotfix only error-class mapping/observability.

## Escalation

Escalate to backend owner if valid-token failures exceed 1% for 10 minutes.
