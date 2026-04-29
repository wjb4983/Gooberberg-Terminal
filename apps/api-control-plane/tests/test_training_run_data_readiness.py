from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_market_data_service, get_model_config_service
from app.main import create_app
from app.schemas import (
    MarketDataCacheCoverageResponse,
    MarketDataDatasetLookupResponse,
    MarketDataIngestionResponse,
)

MODEL_CONFIG_ID = UUID("33333333-3333-3333-3333-333333333333")
DATASET_ID = "mds_fixture_dataset"


class StubModelConfigService:
    def get(self, model_config_id: UUID) -> dict[str, object] | None:
        if model_config_id != MODEL_CONFIG_ID:
            return None
        return {
            "id": str(model_config_id),
            "model_family": "arima",
            "config": {"p": 1, "d": 1, "q": 0},
        }


class StubMarketDataService:
    def __init__(self, coverage: MarketDataCacheCoverageResponse) -> None:
        self._coverage = coverage
        self.ingestion_requests: list[dict[str, object]] = []

    def lookup_dataset(self, dataset_id: str) -> MarketDataDatasetLookupResponse | None:
        if dataset_id != DATASET_ID:
            return None
        return MarketDataDatasetLookupResponse(
            dataset_id=DATASET_ID,
            source="stub",
            symbol="AAPL",
            timeframe="1d",
            metadata={
                "data_kind": "time_series",
                "index_type": "datetime",
                "target_type": "regression",
                "provider": "massive",
                "asset_class": "stocks",
                "symbols": ["AAPL"],
                "resolutions": ["1d"],
                "start_date": "2025-01-01",
                "end_date": "2025-01-02",
            },
        )

    def get_cache_coverage(self, symbol: str, timeframe: str) -> MarketDataCacheCoverageResponse:
        assert symbol == "AAPL"
        assert timeframe == "1d"
        return self._coverage

    def request_ingestion(self, payload) -> MarketDataIngestionResponse:
        self.ingestion_requests.append(payload.model_dump(mode="json"))
        return MarketDataIngestionResponse(
            request_id="ingestion-1",
            dataset_id="ingestion-1",
            status="accepted",
            source=payload.provider,
            symbols=payload.universe_members,
            timeframe=payload.resolutions[0],
        )


def _test_client(stub_market_data_service: StubMarketDataService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_model_config_service] = lambda: StubModelConfigService()
    app.dependency_overrides[get_market_data_service] = lambda: stub_market_data_service
    return TestClient(app)


def _training_payload() -> dict[str, object]:
    return {
        "model_config_id": str(MODEL_CONFIG_ID),
        "dataset_id": DATASET_ID,
        "task_type": "time_series_momentum",
        "subtask_type": "ranking",
        "parameters": {"epochs": 1},
    }


def test_training_run_starts_queued_and_can_move_to_running() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
            coverage_pct=100.0,
        )
    )

    with _test_client(market_data_service) as client:
        create_response = client.post("/api/v1/training-runs", json=_training_payload())
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "queued"

        running_response = client.post(
            f"/api/v1/jobs/{created['job_id']}/events",
            json={
                "status": "running",
                "detail": "training started",
                "progress_pct": 5.0,
                "message": "running",
            },
        )
        assert running_response.status_code == 200

        fetched = client.get(f"/api/v1/training-runs/{created['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "running"

    assert market_data_service.ingestion_requests == []


def test_training_run_with_partial_coverage_waits_for_data_and_enqueues_ingestion() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 2),
            available_end=date(2025, 1, 2),
            coverage_pct=50.0,
        )
    )

    with _test_client(market_data_service) as client:
        create_response = client.post("/api/v1/training-runs", json=_training_payload())
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["status"] == "waiting_for_data"

        events_response = client.get(f"/api/v1/jobs/{created['job_id']}/events")
        assert events_response.status_code == 200
        statuses = [event["status"] for event in events_response.json()]
        assert statuses == ["queued", "waiting_for_data"]

    assert len(market_data_service.ingestion_requests) == 1
    assert market_data_service.ingestion_requests[0]["universe_members"] == ["AAPL"]
    assert market_data_service.ingestion_requests[0]["resolutions"] == ["1d"]


def test_duplicate_dataset_ingestion_with_same_spec_returns_same_dataset_id() -> None:
    with TestClient(create_app()) as client:
        payload = {
            "provider": "massive",
            "asset_class": "stocks",
            "universe_members": ["AAPL"],
            "resolutions": ["1d"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
        }

        first = client.post("/api/v1/market-data/ingestions", json=payload)
        second = client.post("/api/v1/market-data/ingestions", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    first_payload = first.json()
    second_payload = second.json()
    assert second_payload["request_id"] == first_payload["request_id"]
    assert second_payload["dataset_id"] == first_payload["dataset_id"]
    assert second_payload["status"] == "already_exists"


def test_training_run_preflight_returns_normalized_payload() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
            coverage_pct=100.0,
        )
    )

    with _test_client(market_data_service) as client:
        response = client.post(
            "/api/v1/training-runs/preflight",
            json={
                "model_config_id": str(MODEL_CONFIG_ID),
                "dataset_id": f" {DATASET_ID} ",
                "task_type": "time_series_momentum",
                "subtask_type": "ranking",
                "parameters": {"epochs": 2},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["compatible"] is True
    assert body["normalized_payload"]["dataset_id"] == DATASET_ID
    assert body["training_intent"]["task_type"] == "time_series_momentum"
    assert body["training_intent"]["model_family"] == "arima"
    assert body["training_intent"]["dataset_id"] == DATASET_ID
    assert body["training_intent"]["validation_profile"] == "walk_forward"
    assert len(body["warnings"]) == 1



def test_training_run_preflight_uses_explicit_validation_profile() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
            coverage_pct=100.0,
        )
    )

    with _test_client(market_data_service) as client:
        response = client.post(
            "/api/v1/training-runs/preflight",
            json={
                **_training_payload(),
                "validation_profile": "purged_k_fold",
            },
        )

    assert response.status_code == 200
    assert response.json()["training_intent"]["validation_profile"] == "purged_k_fold"


def test_training_run_create_persists_training_intent_in_run_metadata() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
            coverage_pct=100.0,
        )
    )

    with _test_client(market_data_service) as client:
        create_response = client.post("/api/v1/training-runs", json=_training_payload())

    assert create_response.status_code == 201
    body = create_response.json()
    run_metadata = body["parameters"]["run_metadata"]
    assert run_metadata["training_intent"]["task_type"] == "time_series_momentum"
    assert run_metadata["training_intent"]["subtask_type"] == "ranking"
    assert run_metadata["training_intent"]["model_family"] == "arima"
    assert run_metadata["training_intent"]["dataset_id"] == DATASET_ID
    assert run_metadata["training_intent"]["validation_profile"] == "walk_forward"

def test_training_run_compatibility_reports_missing_dataset() -> None:
    market_data_service = StubMarketDataService(
        coverage=MarketDataCacheCoverageResponse(
            symbol="AAPL",
            timeframe="1d",
            available_start=date(2025, 1, 1),
            available_end=date(2025, 1, 2),
            coverage_pct=100.0,
        )
    )

    with _test_client(market_data_service) as client:
        response = client.post(
            "/api/v1/training-runs/compatibility",
            json={
                "model_config_id": str(MODEL_CONFIG_ID),
                "dataset_id": "missing_dataset",
                "task_type": "time_series_momentum",
                "subtask_type": "ranking",
                "parameters": {"epochs": 2},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["compatible"] is False
    assert "dataset not found; ingest data and retry" in body["errors"]
