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
- `GET /api/v1/runs/{run_id}/lineage`
- `GET /api/v1/runs/{run_id}/artifacts`
- `GET /api/v1/runs/{run_id}/replay`

## Run replay and integrity contracts

### `GET /api/v1/runs/{run_id}/lineage`

Returns a canonical lineage block plus lineage schema version:

- `schema_version`: lineage payload schema identifier (currently `v1`).
- `lineage`: immutable replay inputs (`dataset_fingerprint`, `code_hash`, `config_digest`, `seed`) and lineage processing status metadata.

### `GET /api/v1/runs/{run_id}/artifacts`

Returns:

- `manifest_entries`: ordered artifact manifest records (`artifact_role`, refs, uris, creation time).
- `integrity_metadata`: per-artifact checksums (`checksum`, `sha256`), signatures, and size bytes for independent verification.

### `GET /api/v1/runs/{run_id}/replay`

Replay helper payload includes:

- `replay_bundle.dataset_reference`
- `replay_bundle.code_hash`
- `replay_bundle.normalized_config`
- `replay_bundle.seed`
- `integrity_attestations` (lineage version/status plus artifact cardinality)
- `missing_prerequisites` list when replay-critical material is incomplete.

## Contract guarantees for run durability

### Immutable post-run fields

After a run transitions into terminal status, these fields are treated as immutable for replay and audit:

- `dataset_fingerprint`
- `code_hash`
- `config_digest`
- `seed`
- artifact integrity tuple (`checksum`, `sha256`, `size_bytes`, `signature`) per manifest entry

### Independent artifact verification

Clients verify artifacts by:

1. Fetching artifact bytes from `artifact_ref` / `artifact_uri`.
2. Recomputing digest (`sha256`) and checking returned `checksum`.
3. Validating `size_bytes`.
4. Optionally validating `signature` against client trust policy.

### Lineage schema version evolution

- `schema_version` is explicit on lineage responses.
- Additive lineage fields are backwards-compatible within a schema version.
- Breaking lineage shape changes require a new `schema_version` value and dual-read compatibility window in clients.

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
