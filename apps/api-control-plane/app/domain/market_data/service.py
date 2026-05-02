from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status

from app.domain.market_data.repository import Repository
from app.schemas import (
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
)


@dataclass(frozen=True)
class IngestionPreset:
    provider: str
    asset_class: str
    universe_members: list[str]
    resolutions: list[str]
    start_date: str
    end_date: str
    allow_manual_symbols: bool


INGESTION_PRESETS: dict[str, IngestionPreset] = {
    "us_stocks_daily_core": IngestionPreset(
        provider="massive",
        asset_class="stocks",
        universe_members=["SPY", "QQQ", "IWM"],
        resolutions=["1d"],
        start_date="2020-01-01",
        end_date="2025-12-31",
        allow_manual_symbols=False,
    ),
    "us_stocks_intraday_flexible": IngestionPreset(
        provider="massive",
        asset_class="stocks",
        universe_members=[],
        resolutions=["1h"],
        start_date="2024-01-01",
        end_date="2025-12-31",
        allow_manual_symbols=True,
    ),
}


class Service:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    def request_ingestion(self, payload: MarketDataIngestionRequest) -> MarketDataIngestionResponse:
        normalized = self._resolve_payload(payload)
        return self._repository.request_ingestion(normalized)

    def _resolve_payload(self, payload: MarketDataIngestionRequest) -> MarketDataIngestionRequest:
        if not payload.preset_id:
            if payload.start_date is None or payload.end_date is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "missing_date_range", "message": "start_date and end_date are required when preset_id is not provided."})
            return payload

        preset = INGESTION_PRESETS.get(payload.preset_id)
        if preset is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_preset_id", "message": f"Unknown preset_id '{payload.preset_id}'."},
            )

        manual_symbols = payload.universe_members or payload.symbols
        if manual_symbols and not preset.allow_manual_symbols:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_override_combination",
                    "message": "Manual symbols are not allowed for this preset.",
                    "preset_id": payload.preset_id,
                    "field": "symbols",
                },
            )

        resolved_start = payload.start_date or date.fromisoformat(preset.start_date)
        resolved_end = payload.end_date or date.fromisoformat(preset.end_date)

        return payload.model_copy(
            update={
                "provider": payload.provider or preset.provider,
                "asset_class": payload.asset_class or preset.asset_class,
                "universe_members": payload.universe_members or preset.universe_members,
                "resolutions": payload.resolutions or preset.resolutions,
                "start_date": resolved_start,
                "end_date": resolved_end,
            }
        )

    def get_cache_coverage(self, symbol: str, timeframe: str) -> MarketDataCacheCoverageResponse:
        return self._repository.get_cache_coverage(symbol, timeframe)

    def lookup_dataset(self, dataset_id: str) -> MarketDataDatasetLookupResponse | None:
        return self._repository.lookup_dataset(dataset_id)
