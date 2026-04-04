from datetime import timedelta

from fastapi import APIRouter, Query, status

from app.schemas import (
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
)

router = APIRouter(prefix="/market-data", tags=["market-data"])

_ingestion_requests: list[MarketDataIngestionResponse] = []


@router.post("/ingestions", response_model=MarketDataIngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def request_market_data_ingestion(payload: MarketDataIngestionRequest) -> MarketDataIngestionResponse:
    response = MarketDataIngestionResponse(
        source=payload.source,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
    )
    _ingestion_requests.append(response)
    return response


@router.get("/cache-coverage", response_model=MarketDataCacheCoverageResponse)
def get_cache_coverage(symbol: str = Query(min_length=1), timeframe: str = Query(min_length=1)) -> MarketDataCacheCoverageResponse:
    return MarketDataCacheCoverageResponse(
        symbol=symbol,
        timeframe=timeframe,
        available_start=None,
        available_end=None,
        coverage_pct=0.0,
    )


@router.get("/datasets/{dataset_id}", response_model=MarketDataDatasetLookupResponse)
def lookup_dataset(dataset_id: str) -> MarketDataDatasetLookupResponse:
    return MarketDataDatasetLookupResponse(
        dataset_id=dataset_id,
        source="mock-cache",
        symbol="SPY",
        timeframe="1d",
        metadata={"records": 0, "stale_after": str(timedelta(hours=24))},
    )
