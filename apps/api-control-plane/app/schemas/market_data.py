from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class MarketDataIngestionRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)
    alias: str | None = Field(default=None, min_length=1, max_length=128)
    requested_by: str | None = Field(default=None, min_length=1, max_length=128)
    freshness_sla_days: int = Field(default=30, ge=1, le=3650)
    preset_id: str | None = Field(default=None, min_length=1)
    provider: Literal["massive"] = "massive"
    asset_class: Literal["stocks", "options"] = "stocks"
    universe_members: list[str] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)
    feature_recipe_version: str = Field(default="v1", min_length=1)
    label_recipe_version: str = Field(default="v1", min_length=1)
    start_date: date | None = None
    end_date: date | None = None

    # Backward-compatible legacy fields.
    source: str | None = Field(default=None, min_length=1)
    symbols: list[str] = Field(default_factory=list)
    timeframe: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _normalize_legacy_fields(self) -> "MarketDataIngestionRequest":
        if not self.universe_members and self.symbols:
            self.universe_members = self.symbols
        if not self.resolutions and self.timeframe:
            self.resolutions = [self.timeframe]
        if not self.resolutions:
            self.resolutions = ["1d"]
        return self


class MarketDataIngestionResponse(BaseModel):
    request_id: str
    dataset_id: str | None = None
    status: str = "accepted"
    source: str
    symbols: list[str] = Field(default_factory=list)
    timeframe: str
    effective_params: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)


class MarketDataBatchIngestionRequest(BaseModel):
    preset_ids: list[str] = Field(default_factory=list, min_length=1)
    requested_by: str | None = Field(default=None, min_length=1, max_length=128)
    idempotency_key_prefix: str | None = Field(default=None, min_length=1, max_length=64)


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
