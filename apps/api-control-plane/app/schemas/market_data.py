from datetime import date
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MarketDataIngestionRequest(BaseModel):
    source: str = Field(min_length=1)
    symbols: list[str] = Field(default_factory=list)
    timeframe: str = Field(min_length=1)
    start_date: date
    end_date: date


class MarketDataIngestionResponse(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    status: str = "accepted"
    source: str
    symbols: list[str] = Field(default_factory=list)
    timeframe: str


class MarketDataCacheCoverageResponse(BaseModel):
    symbol: str
    timeframe: str
    available_start: date | None = None
    available_end: date | None = None
    coverage_pct: float = 0.0


class MarketDataDatasetLookupResponse(BaseModel):
    dataset_id: str
    source: str
    symbol: str
    timeframe: str
    metadata: dict[str, Any] = Field(default_factory=dict)
