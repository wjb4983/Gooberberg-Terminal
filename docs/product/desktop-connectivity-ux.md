# Desktop Connectivity UX Spec (v1)

- **Feature flag:** `desktop_connectivity_diagnostics_v1`
- **Status:** Draft for product/design review
- **Scope:** Desktop Tauri connectivity onboarding, diagnostics, and recovery UX (no implementation in this phase)
- **Primary surfaces:**
  - `apps/desktop-tauri/src/pages/SettingsPage.tsx`
  - `apps/desktop-tauri/src/components/SystemStatusBar.tsx`
  - `apps/desktop-tauri/src/components/ApiErrorCallout.tsx`

---

## 1) Goals and non-goals

## Goals

1. Help operators configure connectivity correctly on first run with clear guardrails.
2. Make transport health legible without requiring logs or terminal access.
3. Provide immediate, explicit recovery actions mapped 1:1 to supported backend/client capabilities.
4. Keep existing workflow safe by shipping behind a flag and preserving rollback path.

## Non-goals

1. No backend protocol changes in this phase.
2. No automated self-healing beyond explicit user-triggered actions.
3. No advanced network debugging tools (packet capture, traceroute, etc.).

---

## 2) First-run onboarding wizard

### Entry conditions

Show wizard when either:
- no base URL is configured, or
- token is missing, or
- user clicks **Re-run setup wizard** from Settings.

### Steps and UX behavior

1. **Base URL setup**
   - Input: `API Base URL`
   - Helper examples:
     - `http://localhost:8000`
     - `http://100.x.y.z:8000` (Tailscale)
     - `https://ops-proxy.example.com/api`
   - Validation:
     - Must be absolute URL.
     - Strip trailing slash only at save time.
   - CTA: **Continue** (disabled until valid URL)

2. **Token test**
   - Input: `Access token`
   - Action: `Test token`
   - Behavior:
     - POST/GET to authenticated probe endpoint.
     - Show spinner and elapsed time.
     - Persist token only on success or explicit user confirmation.
   - Success copy:
     - **Token accepted.** “Authentication succeeded.”
   - Failure copy:
     - **Token rejected (401/403).** “Check token value, spacing, and environment.”

3. **Endpoint probe**
   - Automatic probe sequence:
     - Liveness endpoint
     - API health endpoint
     - Queue heartbeat endpoint
   - Output:
     - Per-check status row with timestamp and duration.
     - Expandable details for non-2xx responses.
   - CTA: **Continue** enabled if liveness + API are reachable (queue may be degraded but non-blocking).

4. **WebSocket subscribe test**
   - Action: open WS, subscribe to a diagnostics topic, wait for ack/first event within timeout.
   - Output:
     - Connected / reconnecting / failed state.
     - Last event timestamp if available.
   - Success copy:
     - **Realtime updates verified.** “Live diagnostics stream is active.”
   - Failure copy:
     - **Realtime stream unavailable.** “You can proceed in degraded mode and retry later.”
   - CTA:
     - **Finish setup** (always available)
     - Secondary: **Retry WebSocket test**

### Wizard wireframe (low fidelity)

```text
+----------------------------------------------------------+
| Connect to Backend (Step 3 of 4)                         |
|----------------------------------------------------------|
| Endpoint Probe                                            |
| Base URL: http://100.88.77.66:8000                       |
|                                                           |
| [✓] Liveness            2026-04-23 14:02:18 UTC   58 ms  |
| [✓] API Health          2026-04-23 14:02:18 UTC   74 ms  |
| [!] Queue Heartbeat     2026-04-23 14:02:19 UTC  3000 ms |
|     details: timeout waiting for queue heartbeat          |
|                                                           |
| [Back]                                  [Continue]        |
+----------------------------------------------------------+
```

---

## 3) Diagnostics panel (Settings)

### Panel contents

A new **Connectivity Diagnostics** section in `SettingsPage` containing:

1. **Current profile**
   - Active endpoint profile chip: `localhost` / `tailscale` / `proxy`
   - Base URL preview

2. **Transport health grid** (four rows)
   - **Liveness**
   - **API**
   - **Queue**
   - **WebSocket**

Each row includes:
- Status pill (`Healthy`, `Degraded`, `Offline`, `Reconnecting`)
- Last checked timestamp (UTC)
- Last success timestamp
- Latency/duration if applicable
- “View details” disclosure

3. **Details drawer**
   - Request URL + method
   - Status code / error class
   - Correlation/request id when present
   - Retry count and next retry backoff
   - **Copy error context** button (copies structured JSON)

### Copyable error context JSON schema

```json
{
  "surface": "settings.diagnostics",
  "check": "websocket",
  "state": "reconnecting",
  "baseUrl": "https://ops-proxy.example.com/api",
  "profile": "proxy",
  "timestamp": "2026-04-23T14:08:11Z",
  "httpStatus": null,
  "errorCode": "ws_reconnecting",
  "message": "WebSocket disconnected; retrying with backoff",
  "requestId": "optional",
  "retryAttempt": 3
}
```

---

## 4) Recovery actions

Recovery actions appear in both diagnostics panel and critical `ApiErrorCallout` states.

1. **Retry now**
   - Triggers immediate re-probe sequence for failed checks.
   - Bypasses scheduled backoff once.

2. **Reset token**
   - Clears stored token and opens secure token input modal.
   - Re-runs token test before saving.

3. **Switch endpoint profile**
   - One-click preset switch:
     - `localhost` → `http://localhost:8000`
     - `tailscale` → `http://<tailscale-ip>:8000`
     - `proxy` → `https://<proxy-host>/api`
   - Triggers full probe sequence after switch.

4. **Open runbook**
   - Opens `docs/runbooks/tauri-backend-connectivity-baseline.md` (or hosted equivalent) in external browser.

### Mapping requirement (acceptance-critical)

Each action must map directly to existing backend/client capabilities:
- Retry uses existing probe and WS reconnect APIs.
- Reset token uses existing secure token storage flow.
- Switch profile updates current base URL contract only (no protocol mutation).
- Runbook link is static configuration.

---

## 5) UX state model design (no implementation yet)

## Global connectivity machine

```text
unconfigured
  └─(base URL + token provided)→ probing
probing
  ├─(all critical checks pass)→ connected
  ├─(critical pass, optional fail)→ degraded
  ├─(critical checks fail)→ offline
  └─(user triggers recovery)→ recovering
connected
  ├─(non-critical check fails)→ degraded
  ├─(critical check fails)→ offline
  └─(user edits config)→ probing
degraded
  ├─(checks recover)→ connected
  ├─(critical checks fail)→ offline
  └─(user recovery action)→ recovering
offline
  ├─(probe succeeds)→ connected/degraded
  └─(user recovery action)→ recovering
recovering
  ├─(recovery succeeds)→ connected/degraded
  └─(recovery fails)→ offline
```

### State ownership by component/page

## `SettingsPage.tsx`

- **Owns canonical diagnostics state** (source of truth).
- Maintains:
  - configured profile/base URL/token presence
  - probe results for liveness/API/queue/WS
  - timestamps + expanded error details
  - in-flight recovery action state
- Exposes selectors to children (status bar + callout integration hooks).

## `SystemStatusBar.tsx`

- **Derived/summary state only** from page/global store.
- Displays compact badge:
  - `Connected` (green)
  - `Degraded` (amber)
  - `Offline` (red)
  - `Recovering…` (blue pulse)
- Shows tooltip with last success + failing subsystem count.
- No direct mutation except “open diagnostics” navigation intent.

## `ApiErrorCallout.tsx`

- **Contextual error presenter** for route-level failures.
- Receives normalized error taxonomy object + recommended action list.
- Renders critical alert copy and high-priority actions:
  - Retry now
  - Reset token (for auth failures)
  - Switch endpoint profile (for DNS/TLS/proxy mismatch)
  - Open runbook

---

## 6) Error taxonomy (user-facing)

All connectivity errors normalize into one of the following categories.

| Error category | Detection signal | User-facing title | User-facing message | Default recovery actions |
|---|---|---|---|---|
| `auth_failure` | HTTP 401/403 | **Authentication failed** | “The access token was rejected by the server.” | Reset token, Retry now |
| `dns_tls_failure` | DNS resolution error, TLS handshake/cert errors | **Can’t establish secure connection** | “We couldn’t resolve or validate the server address.” | Switch endpoint profile, Retry now, Open runbook |
| `timeout` | Request/WS connect exceeds timeout budget | **Server took too long to respond** | “The connection timed out before the backend replied.” | Retry now, Switch endpoint profile |
| `proxy_path_mismatch` | 404/405 on expected API base path under proxy profile | **Proxy path may be incorrect** | “The server is reachable, but the API path appears wrong.” | Switch endpoint profile, Open runbook |
| `stale_heartbeat` | Queue heartbeat older than stale threshold | **Queue heartbeat is stale** | “Background processing may be delayed or paused.” | Retry now, Open runbook |
| `ws_reconnecting` | WS disconnected with active retry/backoff | **Realtime feed reconnecting** | “Live updates are temporarily interrupted while we reconnect.” | Retry now, Switch endpoint profile |

### Critical alert exact copy

1. **Authentication failed**
   - “Your token was rejected (401/403). Reset the token and try again.”
2. **Can’t establish secure connection**
   - “DNS/TLS validation failed for the configured endpoint. Verify host, certificate, or switch profile.”
3. **Server took too long to respond**
   - “The request timed out. The backend may be unavailable or unreachable from this network.”
4. **Proxy path may be incorrect**
   - “Connected to proxy host, but API path did not match expected route.”
5. **Queue heartbeat is stale**
   - “Queue heartbeat is out of date. Some operations may be delayed.”
6. **Realtime feed reconnecting**
   - “WebSocket disconnected; reconnect is in progress. Data shown may be delayed.”

---

## 7) Wireframes and critical surfaces

## A) Settings diagnostics section

```text
+----------------------------------------------------------------+
| Connectivity Diagnostics                                        |
| Profile: [tailscale ▼]    Base URL: http://100.88.77.66:8000   |
|----------------------------------------------------------------|
| Liveness   [Healthy]     Last check 14:08:01   Last OK 14:08:01|
| API        [Healthy]     Last check 14:08:01   Last OK 14:08:01|
| Queue      [Degraded]    Last check 14:08:04   Last OK 14:02:33|
| WebSocket  [Reconnecting]Last check 14:08:05   Last OK 14:07:59|
|                                                                |
| [Retry now] [Reset token] [Switch profile] [Open runbook]      |
+----------------------------------------------------------------+
```

## B) Status bar compact state

```text
[ ● Degraded ]  (tooltip: Queue stale 5m, WS reconnecting)
```

## C) API error callout

```text
! Authentication failed
Your token was rejected (401/403). Reset the token and try again.
[Reset token] [Retry now] [Open runbook]
```

---

## 8) Estimate, ownership, risks, dependencies

- **Estimate:** 3–4 engineering days + 1 design day.
- **Owner profile:** Product-minded frontend engineer + design reviewer.
- **Risk:** Overly technical diagnostics may overwhelm non-technical operators.
- **Dependency:** Phase 1 transport state definitions.

### Mitigations for primary risk

1. Default collapsed advanced details; show plain-language summaries first.
2. Use severity-based progressive disclosure (critical copy first, technical payload second).
3. Keep action labels task-oriented (Retry now / Reset token) rather than protocol-oriented.

---

## 9) Acceptance criteria

1. UX spec is approved by product + design with:
   - wireframes for onboarding, diagnostics, status bar, and callout;
   - exact copy for all critical alerts.
2. Recovery actions map 1:1 to implemented backend/client capabilities.
3. State machine and component ownership are accepted as implementation contract.
4. Feature flag plan reviewed and added to rollout checklist.

---

## 10) Rollout and rollback

## Rollout strategy

- Ship behind `desktop_connectivity_diagnostics_v1`.
- Internal dogfood with proxy + tailscale + localhost profiles.
- Enable progressively per environment after telemetry sanity check.

## Rollback plan

- Disable `desktop_connectivity_diagnostics_v1`.
- Fall back to existing Settings and status bar components.
- Preserve diagnostics code paths but hide UI entry points.
