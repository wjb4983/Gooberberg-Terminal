"""Canonical domain models for market-data ingestion and cataloging."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

Resolution = Literal["minute", "hour", "day"]
AssetClass = Literal["stocks", "options"]
OptionRight = Literal["call", "put"]


class CanonicalBar(BaseModel):
    """Canonical OHLCV bar record used across providers and storage backends."""

    symbol: str = Field(min_length=1)
    ts: datetime = Field(description="Bar open timestamp in UTC.")
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0)
    vwap: float | None = None
    trades: int | None = Field(default=None, ge=0)
    source: str = Field(min_length=1)
    resolution: Resolution
    asset_class: AssetClass = "stocks"
    underlying: str | None = None
    expiry: date | None = None
    strike: float | None = None
    right: OptionRight | None = None

    @field_validator("symbol")
    @classmethod
    def _normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("ts")
    @classmethod
    def _normalize_ts(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @field_validator("underlying")
    @classmethod
    def _normalize_underlying(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @model_validator(mode="after")
    def _validate_asset_key(self) -> "CanonicalBar":
        if self.asset_class == "stocks":
            return self
        if not self.underlying or self.expiry is None or self.strike is None or self.right is None:
            raise ValueError("options bars require underlying, expiry, strike, and right")
        return self


class TimeRange(BaseModel):
    """Closed-open range used for cache coverage lookups."""

    start: datetime
    end: datetime


class DatasetRef(BaseModel):
    """Pointer to a physical dataset partition in object/local storage."""

    ref_id: UUID
    symbol: str
    day: date
    resolution: Resolution
    uri: str
    schema_hash: str
    refreshed_at: datetime


class CoverageRecord(BaseModel):
    """Known covered range for a symbol and resolution."""

    symbol: str
    resolution: Resolution
    start: datetime
    end: datetime
    refreshed_at: datetime


class MissingRange(BaseModel):
    """Known missing range for a symbol and resolution to avoid repeated misses."""

    symbol: str
    resolution: Resolution
    start: datetime
    end: datetime
    reason: str
    detected_at: datetime
