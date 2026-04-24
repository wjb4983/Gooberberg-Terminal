# Desktop Connectivity Auth Hardening Design

## Status
- **In progress** (Phase 2 baseline implemented; pending Security sign-off)
- **Estimate:** 5-7 engineering days + dedicated Security review
- **Owner profile:** Security engineer with API auth and desktop keychain experience

## Goals
1. Replace static shared bearer token usage with scoped, expiring credentials.
2. Enforce least-privilege authorization in the control-plane API.
3. Standardize desktop secret handling and logout/lockout behavior.
4. Mitigate high-priority transport and token abuse threats.

## Non-Goals
- Replacing existing identity provider infrastructure.
- Full zero-trust redesign of every internal service.

## Current State (Summary)
- API currently supports a single static bearer token with coarse scope declaration.
- Desktop storage baseline already prefers OS keychain in Tauri runtime.
- Mixed network topologies exist (localhost, Tailscale, reverse proxy).

---

## 1) Credential Model Migration

### Target model
Move from one static shared token to either:
- **Option A (preferred):** short-lived signed session tokens (JWT/PASETO) with embedded scopes, audience, issued-at, expiry, and token ID.
- **Option B:** opaque scoped credentials with server-side session lookup and short TTL.

### Scope shape
- `control-plane:read` — list/get/watch endpoints.
- `control-plane:write` — create/update/delete/retry/cancel actions.
- `control-plane:admin` — privileged operations (policy/config/admin maintenance), includes write.

### Expiry and refresh
- Access token/session TTL: **15 minutes**.
- Refresh credential TTL: **24 hours** (desktop interactive session).
- Rotation cadence:
  - Signing key rotation every **30 days** (or sooner on incident).
  - Refresh token family rotation at every refresh (rotate-on-use).
- Overlap window for key rollover: **24 hours** with dual validation.

### Revocation behavior
- Immediate revocation by token ID/session ID and user/device binding.
- Keep a revocation set for active TTL + 10 minutes clock skew.
- Force re-auth on:
  - suspected theft,
  - excessive failed auth attempts,
  - key rollover incident mode.

### Migration strategy
- **Dual-mode window:** support legacy static token + new scoped session auth in parallel.
- Emit deprecation warning/audit event on legacy token usage.
- Define strict deprecation date before removal.

### Implemented baseline (April 24, 2026)
- Structured static credentials now support `token_id`, `scope`, and `expires_at`.
- Dual-accept mode supported with multiple configured token records.
- Revocation by token ID supported for emergency response.
- Legacy `GB_API_AUTH_TOKEN` path remains as temporary rollback/fallback mode.

### Rollback plan
- Temporarily re-enable legacy static token validation while keeping:
  - audit logging,
  - rate limits,
  - incident alerting.

---

## 2) Authorization Model (Control Plane)

### Route-level least privilege
- Classify endpoints by action class:
  - **Read-only:** GET/HEAD/OPTIONS list/get/status/replay metadata.
  - **Mutating:** POST/PUT/PATCH/DELETE and control actions (cancel/retry/submit/update).
- Enforce required scope at middleware/dependency layer:
  - read-only requires `control-plane:read` (or stronger).
  - mutating requires `control-plane:write` (or stronger).

### Audit requirements
- Log authorization failures with request ID, route template, method, required scope, granted scope, and client identity.
- Never log raw tokens.

---

## 3) Transport Security and Trust Model

### Minimum TLS posture
- TLS 1.2+ minimum, **TLS 1.3 preferred**.
- Disable weak ciphers and renegotiation.
- Enable HSTS on public/proxied HTTPS surfaces.
- Validate certificate chains and hostnames in desktop client.

### Trust model by topology

#### Localhost mode
- Trust boundary: local machine only.
- Allow loopback-only HTTP for local development when explicitly configured.
- Production desktop builds should default to HTTPS when non-loopback hosts are used.

#### Tailscale mode
- Treat Tailnet as private transport, but keep application-layer auth mandatory.
- Prefer HTTPS with trusted certs even on Tailnet to prevent local interception/misrouting risks.

#### Reverse proxy mode
- TLS termination must preserve secure upstream behavior.
- Require strict upstream auth forwarding rules and header sanitation.
- Reject insecure proxy headers from untrusted hops.

---

## 4) Desktop Token Handling Policy

### Secret storage
- Tauri desktop app stores long-lived secrets in OS keychain only.
- Session/access token may be memory-resident only; persist minimally.

### Secure erase and logout
- Logout path must:
  1. Revoke current session server-side.
  2. Delete keychain entries.
  3. Zeroize in-memory token buffers where practical.
  4. Clear cached auth state and reconnect channels.

### Failed-auth lockout UX
- Progressive delays after repeated failures (e.g., exponential backoff).
- Hard lockout threshold with clear recovery path (re-auth + optional device verification).
- Surface non-sensitive error reason to user (expired/invalid/revoked).

### Non-Tauri fallback policy
- In non-Tauri contexts (CLI/dev web shell): **in-memory only**, no disk persistence.
- Tokens expire quickly and require explicit re-auth per session.

---

## 5) Threat-Model Exercises and Mitigations

### A) MITM via misconfigured proxy/TLS termination
- **Threat:** termination on weak/insecure edge permits interception.
- **Mitigations:** TLS policy enforcement, strict proxy config validation, hostname/cert pinning options for managed deployments.

### B) Token leakage in logs/crash reports
- **Threat:** bearer material appears in app/server logs.
- **Mitigations:** centralized redaction filters, structured logging allow-list, crash report scrubbing, auth header stripping.

### C) Replay/forged WebSocket messages
- **Threat:** attacker replays or injects stale/forged control messages.
- **Mitigations:** server-sequenced events, nonce/timestamp validation for client control frames, short replay window, signature verification where needed.

---

## Dependencies
- **Phase 1:** endpoint/auth inventory (source of truth for scope mapping).
- **Phase 3:** transport state model completion (localhost vs Tailscale vs proxy topology rules).

## Risks
- Auth migration can break existing automation/scripts using legacy static token behavior.

## Acceptance Criteria
1. Security review sign-off with mitigations mapped to identified threats.
2. Documented token rotation with tested expiry and re-auth flows.
3. Dual-mode rollout completed with communicated deprecation date and rollback playbook.
