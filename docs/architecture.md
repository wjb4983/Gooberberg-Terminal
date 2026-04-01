# Architecture

This document describes the current runtime architecture for the Gooberberg control plane, with special focus on **fast vs slow path**, **risk/execution authority**, and **data handling boundaries**.

## 1) System topology

At runtime, the primary control-plane stack is:

- `api-control-plane` (FastAPI): authenticated control-plane API + WebSocket fanout.
- Redis: job state persistence, job queue, portfolio pub/sub feed.
- Postgres: configured dependency for durable relational data (connectivity checks are currently placeholder in health endpoint).
- Optional nginx edge profile: TLS termination and public ingress.

Compose topology and network exposure are defined in `infra/compose/docker-compose.prod.yml` with private/internal defaults (Redis/Postgres not publicly published). 

## 2) Fast path vs slow path

### Fast path (request/response + lightweight fanout)

The fast path is synchronous API behavior intended for low-latency operator workflows:

1. Client calls FastAPI HTTP endpoint.
2. API validates payload and performs lightweight in-memory decisions.
3. API persists minimal state (in-memory + Redis when configured).
4. API publishes event envelopes to subscribed WebSocket clients.
5. API responds immediately (typically with accepted/current status).

Representative fast-path flows:

- `POST /api/v1/jobs`: creates `JobEnvelope`, emits initial `queued` lifecycle event, pushes queue/state into Redis repository when available, and broadcasts to `jobs` + `logs` WS topics.
- `GET /api/v1/jobs/{id}`: reads from in-memory job store first, then Redis fallback.
- `POST /api/v1/strategies/instances/{id}/start`: evaluates intent through `RiskExecutionAuthority` and either rejects immediately (`403`) or marks strategy running.
- `GET /api/v1/portfolio/snapshot`: returns latest in-memory cached snapshot.

### Slow path (asynchronous, external, or heavyweight execution)

The slow path is any activity that should not block control-plane request latency:

- Downstream workers consuming Redis job queue.
- Strategy/model execution engines.
- Large analytical/result datasets.
- Historical reporting or expensive recomputation.

Control-plane contract for slow path is **reference-based completion**:

- Job lifecycle updates can return a `result_ref` (pointer/URI) instead of embedding large payloads.
- WebSocket events mirror lifecycle status and may include these refs.

Operationally: keep control-plane payloads small and route heavy compute + large data into worker services/storage.

## 3) Risk / execution authority workflow

Risk gating is currently enforced at strategy start:

1. Strategy instance is created with an attached `StrategyIntent`.
2. Start request calls `risk_authority.consume_intent(intent)`.
3. Authority resolves effective limits from base config + optional override.
4. Authority emits an `ExecutionDecision` with approval flag and reason code.
5. If rejected, API returns `403` and strategy remains non-running.
6. If approved, strategy transitions to `running`; WS `strategy` event includes decision reference in detail.

### Override and audit surfaces

- Operators can manage overrides via `/api/v1/risk/overrides`.
- Recent decisions are queryable via `/api/v1/risk/decisions/recent`.
- Authority stores override and decision audit trails in memory for event provenance.

### Decision semantics (current)

Common rejection reasons include:

- `MISSING_ORDER_FIELDS`
- `MAX_QUANTITY_EXCEEDED`
- `MAX_NOTIONAL_EXCEEDED`

This creates a deterministic, explainable control-plane gate before execution handoff.

## 4) Data handling policy

### Control plane payload policy: JSON-first

The API and WebSocket control plane uses JSON DTOs/events only:

- HTTP request/response bodies are JSON.
- WS envelopes are JSON with `event_id`, `seq`, `topic`, `timestamp`, `payload`, `version`.
- Operational metadata (trace IDs, status details, lightweight attributes) remains in control-plane payloads.

### Bulk data policy: reference-first

For large or columnar outputs, do **not** inline data into API/WS payloads.

- Use URI references (`result_ref`, `artifact_ref`, etc.) in control-plane messages.
- Store heavy payloads externally (e.g., object storage paths to Arrow/Parquet artifacts).
- Clients resolve references through data-plane readers/services.

### Arrow/Parquet guidance

- Use Arrow/Parquet for analytical, tabular, and batch outputs.
- Pass only immutable refs in control-plane JSON.
- Version refs by run/job/model version.
- Preserve schema compatibility and retention policy outside control-plane contracts.

## 5) WebSocket eventing model

- Clients connect to `/ws` and explicitly subscribe to topics.
- Topics currently include `jobs`, `alerts`, `logs`, `portfolio`, `risk`, `strategy`, `models`.
- Server sends heartbeat `ping`; client may reply `pong`/`ping`.
- Invalid messages receive structured error events.
- Per-process event sequencing (`seq`) supports ordering per server instance.

## 6) Auth and trust boundary

- Control plane uses static bearer-token middleware.
- Health paths are exempt for liveliness probes.
- All other endpoints require exact `Authorization: Bearer <token>` when token configured.

## 7) Known limitations and roadmap implications

Current implementation intentionally keeps some pieces lightweight:

- Health endpoint reports Postgres/Redis connectivity as placeholder fields (configured status + placeholder detail).
- Risk authority state is process-local (in-memory).
- WS resume query parameter is accepted by client construction but server-side resume replay is not implemented.

When hardening for multi-instance production, prioritize:

1. Durable risk/decision store.
2. Real dependency probes and SLO-centric health states.
3. Replayable event log for WS resume.
4. Explicit data-plane service for Arrow/Parquet retrieval.
