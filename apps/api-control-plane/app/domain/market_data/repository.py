from app.persistence.repositories import MarketDataSqlRepository
from app.schemas import (
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
)


class Repository:
    def __init__(self, sql_repository: MarketDataSqlRepository) -> None:
        self._repository = sql_repository

    def request_ingestion(self, payload: MarketDataIngestionRequest) -> MarketDataIngestionResponse:
        return self._repository.request_ingestion(payload)

    def get_cache_coverage(self, symbol: str, timeframe: str) -> MarketDataCacheCoverageResponse:
        return self._repository.get_cache_coverage(symbol, timeframe)

    def lookup_dataset(self, dataset_id: str) -> MarketDataDatasetLookupResponse | None:
        return self._repository.lookup_dataset(dataset_id)
