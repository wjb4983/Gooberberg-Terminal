"""Provider adapters for market-data ingestion."""

from service_data.market_data.providers.base import MarketDataProvider, ProviderError
from service_data.market_data.providers.massive_adapter import MassiveAdapter

__all__ = ["MarketDataProvider", "ProviderError", "MassiveAdapter"]
