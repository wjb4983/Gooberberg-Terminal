# API Contracts: FastAPI ↔ TypeScript

## Goal
Provide a stable, shared contract between:

- **FastAPI control-plane service** (`apps/api-control-plane`)
- **TypeScript packages** (`libs/ts/@gb/schemas`, `libs/ts/@gb/api-client`)
- **Desktop app consumer** (`apps/desktop-tauri`)

## Contract layers

1. **Runtime HTTP/WS schema authority:** FastAPI OpenAPI and router behavior.
2. **Stable app-facing TypeScript contract:** `@gb/schemas` curated types.
3. **Transport/runtime parsing:** `@gb/api-client` request adapters and payload parsers.

This protects app code from backend naming/shape churn while preserving type-safe contracts.

## Fast path vs slow path contract

### Fast path contract (control plane)

Use JSON payloads for:

- Health + topology + current status.
- Job submission/ack and lifecycle state.
- Strategy/risk control actions.
- WS event envelopes and lightweight payloads.

### Slow path contract (data plane)

For heavy outputs or artifacts:

- Return pointers like `result_ref` / `artifact_ref`.
- Do not embed large tabular payloads directly in API or WS events.
- Resolve refs through data services/object storage readers.

## Data handling policy

### JSON control plane (required)

- HTTP DTOs and WS envelopes are JSON.
- Keep control-plane payloads small and operationally focused (IDs, status, timestamps, reason/detail, refs).

### Arrow/Parquet references (required for bulk)

- Large tabular outputs should be produced as Arrow/Parquet artifacts.
- Control-plane returns only immutable reference strings/URIs.
- Include enough metadata in control plane for discoverability (job/model/version identifiers).

## Current endpoint surface

### HTTP

- `GET /api/v1/health`
- `GET /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/ack`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/events`
- `GET /api/v1/portfolio/snapshot`
- `GET /api/v1/graph/topology`
- `GET /api/v1/models/deployments`
- `POST /api/v1/models/deployments`
- `POST /api/v1/models/deployments/{deployment_id}/activate`
- `POST /api/v1/models/deployments/{deployment_id}/deactivate`
- `GET /api/v1/strategies/instances`
- `POST /api/v1/strategies/instances`
- `POST /api/v1/strategies/instances/{instance_id}/start`
- `POST /api/v1/strategies/instances/{instance_id}/stop`
- `GET /api/v1/risk/overrides`
- `POST /api/v1/risk/overrides`
- `GET /api/v1/risk/decisions/recent`

## Run-creation lineage contract

`POST /api/v1/training-runs` and `POST /api/v1/backtest-runs` require either:

1. a full `lineage` object (`LineageSpec`), or
2. a `lineage_ref` object resolvable into lineage before enqueue.

If neither is provided, the API rejects with `422` and reason code
`LINEAGE_VALIDATION_FAILED`.

Accepted (reference-driven) example:

```json
{
  "lineage_ref": {
    "dataset_fingerprint_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "code_git_commit_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "code_dirty": false,
    "seed": 7
  }
}
```

Failure example:

```json
{
  "detail": {
    "message": "lineage validation failed",
    "reason_code": "LINEAGE_VALIDATION_FAILED",
    "errors": [
      { "field": "lineage|lineage_ref", "message": "either lineage or lineage_ref must be provided" }
    ]
  }
}
```

### WebSocket

- `GET ws://<host>/ws`
- Client messages:
  - `{ "action": "subscribe", "topics": [...] }`
  - `{ "action": "unsubscribe", "topics": [...] }`
  - `ping` / `pong`
- Server control messages:
  - `{"type":"ping"}` heartbeat
  - subscribe/unsubscribe acknowledgments
  - error payloads
- Server data messages (topic events):
  - `{ event_id, seq, topic, timestamp, payload, version }`

## Risk/execution authority contract

Strategy start endpoint enforces risk gate before running:

- API consumes strategy intent through `RiskExecutionAuthority`.
- Rejection returns `403` with `risk rejected intent: <reason_code>`.
- Approval transitions strategy state and includes decision reference in returned detail.

Risk API provides:

- Override management (`/risk/overrides`)
- Decision introspection (`/risk/decisions/recent`)

## Compatibility and versioning rules

- Additive fields: minor release.
- Breaking field changes/removals: major release.
- WS topic event envelopes include explicit `version`.
- Backends should preserve previous keys until clients are migrated.

## Update workflow

When backend contracts change:

1. Update FastAPI request/response models and routers.
2. Regenerate OpenAPI typings:
   ```bash
   timeout 3m ./scripts/gen-schemas.sh
   ```
3. Reconcile with stable `@gb/schemas` exports.
4. Update `@gb/api-client` parser/mapping logic.
5. Run checks:
   ```bash
   timeout 10m scripts/lint-all.sh
   timeout 10m scripts/test-all.sh
   ```
6. Ship with semantic versioning discipline.

## Developer rules of thumb

- Keep HTTP/WS payloads operational and compact.
- Put large/binary/tabular data behind `*_ref` links.
- Enforce risk gate before execution transitions.
- Prefer explicit, versioned event contracts over implicit payload assumptions.
