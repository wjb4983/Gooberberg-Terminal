# API Contracts: FastAPI ↔ TypeScript

## Goal
Provide a stable, shared contract between:

- **FastAPI control-plane service** (`apps/api-control-plane`)
- **TypeScript packages** (`libs/ts/@gb/schemas`, `libs/ts/@gb/api-client`)
- **Desktop app consumer** (`apps/desktop-tauri`)

## Source of Truth Strategy
We use a **hybrid contract workflow**:

1. **Runtime API schema source of truth** is FastAPI OpenAPI (`/openapi.json`).
2. **Stable app-facing TypeScript contract** is manually curated in `@gb/schemas`.
3. Optional generated OpenAPI typings live under `@gb/schemas/src/generated/openapi.ts` for diffing and reconciliation.

This approach keeps day-to-day TypeScript imports stable while still allowing contract verification against backend OpenAPI.

## Shared Types (current stable surface)
Defined in `libs/ts/@gb/schemas/src/index.ts`:

- `Job`
- `JobStatus`
- `StrategyInstance`
- `PortfolioSnapshot`
- `AlertEvent`
- `LogEvent`

Event contracts require a versioned envelope through `ContractEnvelopeBase`:

- `version: string`
- `emittedAtIso: string`

`AlertEvent` and `LogEvent` both include this envelope.

## API Client Surface
`libs/ts/@gb/api-client/src/index.ts` exports `GbApiClient` with typed methods:

- `getHealth()`
- `createJob(request)`
- `getJob(jobId)`
- `connectWebSocket(options?)`

### Endpoint mapping
- `getHealth` → `GET /api/v1/health`
- `createJob` → `POST /api/v1/jobs`
- `getJob` → `GET /api/v1/jobs/{job_id}`
- `connectWebSocket` → `GET ws://.../ws`

## Update Workflow
When backend contracts change:

1. Update FastAPI response/request models.
2. Regenerate raw OpenAPI TS types:
   ```bash
   ./scripts/gen-schemas.sh
   ```
3. Reconcile differences into stable `libs/ts/@gb/schemas/src/index.ts`.
4. Update `@gb/api-client` parsing/mapping logic.
5. Run typecheck/build for affected packages.
6. Bump package versions (or changeset) if contract changes are externally visible.

## Versioning Rules
- Additive fields may be introduced in a minor release.
- Breaking field renames/removals require a major release.
- Event envelopes must always include `version` to support forward/backward compatibility.
- If backend introduces a breaking API response shape, update both:
  - `@gb/schemas` stable contract
  - `@gb/api-client` mapping/parsers

## Desktop Integration Note
Desktop should import only from:

- `@gb/schemas` for DTO/event types
- `@gb/api-client` for transport logic and endpoint methods

Avoid re-defining API payload types inside app packages.
