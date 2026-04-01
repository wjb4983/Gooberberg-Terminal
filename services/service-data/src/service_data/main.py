"""Service-data API skeleton focused on metadata references."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    """Closed-open timestamp range that bounds the dataset payload."""

    start: datetime = Field(description="Inclusive start timestamp in UTC.")
    end: datetime = Field(description="Exclusive end timestamp in UTC.")


class MarketDataRef(BaseModel):
    """Metadata pointer to a dataset payload kept outside control-plane APIs."""

    ref_id: UUID = Field(description="Stable identifier for this payload reference.")
    format: Literal["arrow", "parquet"] = Field(
        description="Physical payload format in the data lake."
    )
    uri: str = Field(
        pattern=r"^file:///data/lake/.+",
        description="Local lake URI where the payload can be read.",
    )
    schema_hash: str = Field(
        min_length=8,
        description="Hash of the logical schema associated with this payload.",
    )
    time_range: TimeRange
    symbols: list[str] = Field(min_length=1, description="Covered symbols/tickers.")


class DataRefsQuery(BaseModel):
    """Filter query for metadata references."""

    symbols: list[str] = Field(default_factory=list)
    start: datetime | None = None
    end: datetime | None = None


app = FastAPI(title="service-data", version="0.1.0")

REF_CATALOG: dict[UUID, MarketDataRef] = {}


# Seed placeholder records under /data/lake per acceptance requirements.
_seed_refs = [
    MarketDataRef(
        ref_id=uuid4(),
        format="parquet",
        uri="file:///data/lake/market/trades/date=2026-03-31/part-0000.parquet",
        schema_hash="sha256:trades_v1_abc12345",
        time_range=TimeRange(
            start=datetime(2026, 3, 31, 13, 30, tzinfo=timezone.utc),
            end=datetime(2026, 3, 31, 20, 0, tzinfo=timezone.utc),
        ),
        symbols=["AAPL", "MSFT"],
    ),
    MarketDataRef(
        ref_id=uuid4(),
        format="arrow",
        uri="file:///data/lake/market/quotes/date=2026-03-31/chunk-0001.arrow",
        schema_hash="sha256:quotes_v1_def67890",
        time_range=TimeRange(
            start=datetime(2026, 3, 31, 13, 30, tzinfo=timezone.utc),
            end=datetime(2026, 3, 31, 20, 0, tzinfo=timezone.utc),
        ),
        symbols=["NVDA", "TSLA"],
    ),
]

for ref in _seed_refs:
    REF_CATALOG[ref.ref_id] = ref


@app.post("/data/refs/query", response_model=list[MarketDataRef])
def query_data_refs(query: DataRefsQuery) -> list[MarketDataRef]:
    """Return metadata refs only; never returns raw dataset blobs."""

    refs = list(REF_CATALOG.values())

    if query.symbols:
        requested = {symbol.upper() for symbol in query.symbols}
        refs = [
            ref for ref in refs if requested.intersection({s.upper() for s in ref.symbols})
        ]

    if query.start:
        refs = [ref for ref in refs if ref.time_range.end > query.start]

    if query.end:
        refs = [ref for ref in refs if ref.time_range.start < query.end]

    return refs


@app.get("/data/refs/{ref_id}", response_model=MarketDataRef)
def get_data_ref(ref_id: UUID) -> MarketDataRef:
    """Fetch one metadata pointer by id."""

    ref = REF_CATALOG.get(ref_id)
    if ref is None:
        raise HTTPException(status_code=404, detail="Reference not found")
    return ref


def main() -> None:
    """Run the service_data placeholder entrypoint."""
    print("service_data service skeleton")


if __name__ == "__main__":
    main()
