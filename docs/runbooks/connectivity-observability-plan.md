# Connectivity SLO/SLI + Instrumentation + Synthetic Checks Plan

## Scope

Define measurable reliability objectives for desktop-to-backend connectivity, instrument the stack to support alerting/triage, and provide operational runbooks that on-call can execute without tribal knowledge.

## 1) SLOs and SLIs for Connectivity

All SLIs should be emitted per-environment (`local`, `staging`, `prod`) and per-route class (`health`, `auth`, `core_api`, `ws`).

### SLO-A: API liveness success rate

- **SLI:** `api_liveness_success_rate = successful_requests / total_requests`
- **Population:** HTTP requests to liveness-critical endpoints (`/healthz`, `/api/v1/health`, and one auth-protected canary endpoint).
- **Success criteria:** 2xx/3xx response, or expected 401 for invalid-token synthetic in auth validation lane.
- **Target:**
  - **Production:** `>= 99.9%` per rolling 30 days.
  - **Staging:** `>= 99.5%` per rolling 30 days.

### SLO-B: p95 latency by endpoint class

- **SLI:** `http_request_latency_ms_p95` segmented by endpoint class.
- **Endpoint classes + objectives:**
  - `health`: p95 `< 250ms`
  - `auth`: p95 `< 500ms`
  - `core_api`: p95 `< 900ms`
- **Evaluation window:** 1-hour windows, tracked continuously; alert when sustained breach lasts `>= 15m`.

### SLO-C: WS session stability

- **SLI:** `ws_session_stability = ws_sessions_without_unexpected_disconnect / total_ws_sessions`
- **Unexpected disconnect examples:** connection reset, close code indicating server error, idle timeout before expected heartbeat horizon.
- **Target:**
  - **Production:** `>= 99.5%` per rolling 7 days.

### SLO-D: replay-gap rate

- **SLI:** `replay_gap_rate = ws_reconnects_with_sequence_gap / total_ws_reconnects`
- **Gap definition:** client reconnects with `last_seq`, then detects missing sequence continuity after resume.
- **Target:**
  - **Production:** `< 0.5%` per rolling 7 days.
  - **Staging:** `< 1.0%` per rolling 7 days.

## 2) Instrumentation Plan

### Structured logs

Emit structured JSON logs from both desktop diagnostics layer and backend transport/auth middleware with the following fields:

- `timestamp`, `level`, `service`, `env`, `host`
- `event_name`, `event_id` (desktop diagnostics event ID)
- `request_id` (backend request ID / trace correlation key)
- `route`, `endpoint_class`, `method`, `status_code`
- `auth_result` (`ok`, `missing_header`, `invalid_token`, `expired_token`, `forbidden_scope`)
- `timeout_class` (`connect_timeout`, `read_timeout`, `write_timeout`, `idle_timeout`)
- `retry_count`, `retry_reason`
- `circuit_state` (`closed`, `open`, `half_open`) and `circuit_transition`
- `ws_session_id`, `ws_event`, `ws_reconnect_attempt`, `last_seq`, `gap_detected`

### Metrics

Minimum metric set to add:

- **Auth failures**
  - `auth_failures_total{reason,route}`
- **Timeout classes**
  - `http_timeouts_total{timeout_class,route}`
- **Retry counts**
  - `http_retries_total{reason,route}`
- **Circuit transitions**
  - `circuit_breaker_transitions_total{from_state,to_state,dependency}`
- **WS reconnect loops**
  - `ws_reconnect_attempts_total{reason}`
  - `ws_reconnect_loop_detected_total{session_id}`
- **Core SLO support**
  - `http_requests_total{route_class,status_bucket}`
  - `http_request_duration_ms_bucket{route_class}`
  - `ws_sessions_total{outcome}`
  - `ws_replay_gap_total{topic}`

### Correlation design: desktop event IDs ↔ backend request IDs

1. Desktop generates `event_id` per diagnostics event.
2. Desktop sends `X-Client-Event-ID: <event_id>` with outbound HTTP requests and WS subscribe handshake payload.
3. Backend injects/propagates `X-Request-ID` and logs both IDs together.
4. Dashboards and logs index both IDs for one-click pivot from desktop issue reports to backend traces.

## 3) Synthetic Checks (Environment-Aware)

Synthetic checks run continuously from controlled probes for each environment.

### Check matrix

1. **Localhost backend lane**
   - `http://127.0.0.1:<port>/healthz`
   - Auth-protected endpoint with valid token
   - WS subscribe/ping/pong
2. **Local browser lane**
   - Frontend reachable on `http://127.0.0.1:1420`
   - VS Code forwarded port `1420` opens the same frontend
   - Browser API calls resolve to the local backend

### Synthetic validation steps

Each lane must validate the applicable checks:

1. **Health endpoint:** 200 + expected JSON schema keys.
2. **Auth-protected endpoint:**
   - valid token => 200
   - invalid token => 401 with expected auth error code/classification
3. **WS path:**
   - connect
   - subscribe to topic
   - ping/pong within timeout
   - forced reconnect and continuity check (gap/no-gap classification)

### Alert policy for synthetics

- Start as **non-paging alerts** routed to engineering Slack.
- Promote to paging after **2 weeks** of threshold tuning and false-positive burn-in.

## 4) Runbooks

The following runbooks must exist and be referenced from `docs/runbooks/README.md`:

- `local-server-browser.md`
- `auth-token-rejected.md`
- `ws-reconnect-storm.md`
- `queue-heartbeat-stale.md`

Each runbook contains triage commands and expected outputs.

## 5) Estimate and Ownership

- **Estimate:** `4–6 engineering days`
- **Owner profile:** `SRE/platform engineer + backend engineer`

## Risks

- Alert noise caused by transient reconnects if loop/stability thresholds are too aggressive.

## Dependencies

- Phase 3 telemetry hooks.
- Phase 4 auth event classification.

## Acceptance Criteria

- On-call can execute documented playbooks end-to-end without tribal knowledge.
- Synthetic checks run continuously and alert on regressions.

## Rollout Strategy

1. Deploy instrumentation + dashboards.
2. Enable synthetic checks with non-paging alerts.
3. Baseline and tune thresholds for 2 weeks.
4. Promote stable alerts to paging.

## Rollback Plan

- Downgrade noisy alerts from paging to non-paging while preserving metric/log collection for diagnosis.
