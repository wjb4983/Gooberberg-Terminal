from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_market_data_service, get_model_config_service
from app.main import create_app
from app.schemas import MarketDataDatasetLookupResponse

TIME_SERIES_MODEL_CONFIG_ID = UUID("11111111-1111-1111-1111-111111111111")
CLASSIFICATION_MODEL_CONFIG_ID = UUID("22222222-2222-2222-2222-222222222222")


class StubModelConfigService:
    def get(self, model_config_id: UUID) -> dict[str, object] | None:
        if model_config_id == TIME_SERIES_MODEL_CONFIG_ID:
            return {
                "id": str(model_config_id),
                "model_family": "arima",
                "config": {"p": 1, "d": 1, "q": 0},
            }
        if model_config_id == CLASSIFICATION_MODEL_CONFIG_ID:
            return {
                "id": str(model_config_id),
                "model_family": "hmm_regime_switching",
                "config": {"n_states": 3, "lookback_window": 60},
            }
        return None


class StubMarketDataService:
    def __init__(self) -> None:
        self._datasets = {
            "ts_regression": MarketDataDatasetLookupResponse(
                dataset_id="ts_regression",
                source="stub",
                symbol="AAPL",
                timeframe="1d",
                metadata={
                    "data_kind": "time_series",
                    "index_type": "datetime",
                    "target_type": "regression",
                    "fields": ["ohlcv.close", "timestamp", "entity_id", "returns.log"],
                    "frequency": "1d",
                    "point_in_time_ready": True,
                },
            ),
            "ts_classification": MarketDataDatasetLookupResponse(
                dataset_id="ts_classification",
                source="stub",
                symbol="AAPL",
                timeframe="1d",
                metadata={
                    "data_kind": "time_series",
                    "index_type": "datetime",
                    "target_type": "classification",
                    "fields": ["returns.log", "timestamp"],
                    "frequency": "1d",
                    "point_in_time_ready": True,
                },
            ),
            "tabular_regression": MarketDataDatasetLookupResponse(
                dataset_id="tabular_regression",
                source="stub",
                symbol="AAPL",
                timeframe="",
                metadata={
                    "data_kind": "tabular",
                    "index_type": "row_number",
                    "target_type": "regression",
                    "fields": ["feature_a", "feature_b"],
                    "frequency": "1d",
                    "point_in_time_ready": False,
                },
            ),
        }

    def lookup_dataset(self, dataset_id: str) -> MarketDataDatasetLookupResponse | None:
        return self._datasets.get(dataset_id)


def _test_client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_model_config_service] = lambda: StubModelConfigService()
    app.dependency_overrides[get_market_data_service] = lambda: StubMarketDataService()
    return TestClient(app)


def test_training_run_accepts_time_series_regression_combo() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/training-runs",
            json={
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "dataset_id": "ts_regression",
                "parameters": {"epochs": 1},
            },
        )
    assert response.status_code == 201


def test_training_run_rejects_non_time_series_for_arima() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/training-runs",
            json={
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "dataset_id": "tabular_regression",
                "parameters": {"epochs": 1},
            },
        )
    assert response.status_code == 422
    assert "supports data_kind" in str(response.json()["detail"]) or "supports data_kind" in str(
        response.json()
    )


def test_training_run_rejects_target_type_mismatch() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/training-runs",
            json={
                "model_config_id": str(CLASSIFICATION_MODEL_CONFIG_ID),
                "dataset_id": "ts_regression",
                "parameters": {},
            },
        )
    assert response.status_code == 422
    assert "target_type=classification" in str(response.json())


def test_parameter_sweep_requires_dataset_reference() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/parameter-sweeps",
            json={
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "objective": "maximize_accuracy",
                "search_space": {"lr": [0.001, 0.01]},
                "provenance_snapshot": {},
            },
        )
    assert response.status_code == 422
    assert "provenance_snapshot.dataset_id" in response.json()["detail"]


def test_parameter_sweep_accepts_compatible_dataset() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/parameter-sweeps",
            json={
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "objective": "maximize_accuracy",
                "search_space": {"lr": [0.001, 0.01]},
                "provenance_snapshot": {"dataset_id": "ts_regression"},
            },
        )
    assert response.status_code == 201


def test_backtest_requires_dataset_reference_when_model_config_is_present() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "window_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
                "window_end": datetime(2025, 1, 2, tzinfo=UTC).isoformat(),
                "parameters": {},
            },
        )
    assert response.status_code == 422
    assert "parameters.dataset_id" in response.json()["detail"]


def test_backtest_rejects_target_mismatch() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "model_config_id": str(CLASSIFICATION_MODEL_CONFIG_ID),
                "window_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
                "window_end": datetime(2025, 1, 2, tzinfo=UTC).isoformat(),
                "parameters": {"dataset_id": "ts_regression"},
            },
        )
    assert response.status_code == 422
    assert "target_type=classification" in str(response.json())


def test_backtest_accepts_compatible_dataset() -> None:
    with _test_client() as client:
        response = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "model_config_id": str(TIME_SERIES_MODEL_CONFIG_ID),
                "window_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
                "window_end": datetime(2025, 1, 2, tzinfo=UTC).isoformat(),
                "parameters": {"dataset_id": "ts_regression"},
            },
        )
    assert response.status_code == 201
