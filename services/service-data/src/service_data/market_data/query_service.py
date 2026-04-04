"""Service layer for returning market-data coverage and dataset refs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from service_data.market_data.catalog_repository import CatalogRepository
from service_data.market_data.models import CoverageRecord, DatasetRef, MissingRange, Resolution, TimeRange


class CoverageQuery(BaseModel):
    symbol: str = Field(min_length=1)
    resolution: Resolution = "minute"
    start: datetime
    end: datetime


class CoverageResponse(BaseModel):
    symbol: str
    resolution: Resolution
    coverage: list[CoverageRecord]
    missing: list[MissingRange]
    refs: list[DatasetRef]


class MarketDataQueryService:
    """Query service exposing metadata/coverage only (no large bar payloads)."""

    def __init__(self, *, catalog: CatalogRepository) -> None:
        self.catalog = catalog

    def get_coverage(self, query: CoverageQuery) -> CoverageResponse:
        requested = TimeRange(start=query.start, end=query.end)
        coverage, missing, refs = self.catalog.query_coverage(
            symbol=query.symbol.upper(),
            resolution=query.resolution,
            requested=requested,
        )
        return CoverageResponse(
            symbol=query.symbol.upper(),
            resolution=query.resolution,
            coverage=coverage,
            missing=missing,
            refs=refs,
        )
