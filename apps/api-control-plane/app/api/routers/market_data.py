from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_market_data_service
from app.domain.market_data import Service as MarketDataService
from app.schemas import (
    MarketDataBatchIngestionRequest,
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
    MarketDataProviderCapabilityResponse,
)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.post("/ingestions", response_model=MarketDataIngestionResponse, status_code=status.HTTP_202_ACCEPTED)
def request_market_data_ingestion(
    payload: MarketDataIngestionRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataIngestionResponse:
    return service.request_ingestion(payload)


@router.post("/ingestions/batch", response_model=list[MarketDataIngestionResponse], status_code=status.HTTP_202_ACCEPTED)
def request_market_data_batch_ingestion(
    payload: MarketDataBatchIngestionRequest,
    service: MarketDataService = Depends(get_market_data_service),
) -> list[MarketDataIngestionResponse]:
    return service.request_batch_ingestion(payload)


@router.get("/ingestions", response_model=list[MarketDataIngestionResponse])
def list_market_data_ingestions(
    service: MarketDataService = Depends(get_market_data_service),
) -> list[MarketDataIngestionResponse]:
    return service.list_ingestions()


@router.get("/cache-coverage", response_model=MarketDataCacheCoverageResponse)
def get_cache_coverage(
    symbol: str = Query(min_length=1),
    timeframe: str = Query(min_length=1),
    service: MarketDataService = Depends(get_market_data_service),
) -> MarketDataCacheCoverageResponse:
    return service.get_cache_coverage(symbol=symbol, timeframe=timeframe)


@router.get("/datasets/{dataset_id}", response_model=MarketDataDatasetLookupResponse)
def lookup_dataset(dataset_id: str, service: MarketDataService = Depends(get_market_data_service)) -> MarketDataDatasetLookupResponse:
    item = service.lookup_dataset(dataset_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")
    return item


@router.get("/provider-capabilities", response_model=list[MarketDataProviderCapabilityResponse])
def list_provider_capabilities(
    service: MarketDataService = Depends(get_market_data_service),
) -> list[MarketDataProviderCapabilityResponse]:
    return service.list_provider_capabilities()
