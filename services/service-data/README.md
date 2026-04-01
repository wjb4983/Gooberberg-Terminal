# service-data

Service-data skeleton for reference-based market dataset transfer.

## Purpose

This component exposes **metadata contracts** that point to market data payloads,
instead of returning large Arrow/Parquet blobs over HTTP or WebSocket control-plane
APIs.

## Data contract: `MarketDataRef`

`MarketDataRef` describes where a dataset lives and how to interpret it:

- `format`: Physical payload format (`arrow` or `parquet`).
- `uri`: Lake path URI (placeholder local filesystem paths under `/data/lake`).
- `schema_hash`: Hash that identifies the expected logical schema.
- `time_range`: Time bounds for rows inside the dataset payload.
- `symbols`: Symbol coverage in the payload.

## API skeleton

- `POST /data/refs/query` → returns a filtered list of `MarketDataRef` metadata records.
- `GET /data/refs/{ref_id}` → returns one `MarketDataRef` by identifier.

Both endpoints return **JSON metadata only**. Dataset bytes remain in the lake at the
referenced URI for downstream bulk transfer/read.

## JSON metadata vs Arrow/Parquet payloads

- **JSON metadata (API response):** lightweight control-plane objects for discovery,
  access control, and lineage.
- **Arrow/Parquet payload (data plane):** heavy columnar files stored externally and
  fetched directly from storage paths like `file:///data/lake/...`.

This split encourages scalable, reference-based transfer and avoids oversized API
messages.
