"""Abstract provider contract for ingesting market data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from service_data.market_data.models import CanonicalBar, Resolution


class ProviderError(Exception):
    """Normalized provider-level exception."""

    def __init__(self, code: str, message: str, *, retriable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retriable = retriable


class MarketDataProvider(ABC):
    """Base contract for market-data providers."""

    provider_name: str

    @abstractmethod
    def fetch_bars(
        self,
        *,
        symbol: str,
        start: datetime,
        end: datetime,
        resolution: Resolution,
    ) -> list[CanonicalBar]:
        """Fetch and normalize bars into the canonical schema."""
