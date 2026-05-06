"""Provider adapters for market-data ingestion."""

from service_data.market_data.providers.base import MarketDataProvider, ProviderError
from service_data.market_data.providers.capabilities import (
    ProviderCapabilities,
    get_provider_capabilities,
    list_provider_capabilities,
)
from service_data.market_data.providers.massive_adapter import MassiveAdapter
from service_data.market_data.providers.policy import ProviderPolicy, RetryPolicy

__all__ = [
    "MarketDataProvider",
    "ProviderError",
    "ProviderCapabilities",
    "get_provider_capabilities",
    "list_provider_capabilities",
    "MassiveAdapter",
    "ProviderPolicy",
    "RetryPolicy",
]
