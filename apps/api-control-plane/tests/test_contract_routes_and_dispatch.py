from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.events import WebSocketContractEnvelope


client = TestClient(create_app())


def test_model_config_route_validates_contract_and_persists() -> None:
    payload = {
        "model_family": "hmm_regime_switching",
        "config": {
            "n_states": 3,
            "lookback_window": 64,
            "covariance_type": "diag",
            "convergence_tol": 0.01,
            "max_iterations": 250,
        },
    }

    create_response = client.post("/api/v1/model-configs", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["model_family"] == payload["model_family"]
    assert created["config"]["n_states"] == 3

    get_response = client.get(f"/api/v1/model-configs/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_model_config_route_rejects_invalid_contract_payload() -> None:
    response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "hmm_regime_switching",
            "config": {"n_states": 1, "lookback_window": 5},
        },
    )

    assert response.status_code == 422


def test_model_config_route_accepts_ui_metadata_passthrough_fields() -> None:
    response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "hmm_regime_switching",
            "config": {
                "name": "hmm baseline",
                "version": "v1",
                "task_type": "time_series_momentum",
                "subtask_type": "ranking",
                "data_profile": "time_series",
                "n_states": 3,
                "lookback_window": 64,
                "covariance_type": "diag",
                "convergence_tol": 0.01,
                "max_iterations": 250,
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["config"]["name"] == "hmm baseline"
    assert payload["config"]["version"] == "v1"
    assert payload["config"]["n_states"] == 3


def test_model_config_route_returns_404_for_unknown_model_family() -> None:
    response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "unknown_family",
            "config": {"anything": "goes"},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "POST /api/v1/model-configs: unknown model_family='unknown_family'"


def test_model_config_route_returns_422_for_malformed_known_family_payload_shape() -> None:
    response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "hmm_regime_switching",
            "config": {"n_states": "not-an-int", "lookback_window": "also-not-an-int"},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "POST /api/v1/model-configs: invalid config payload for model_family='hmm_regime_switching'"


def test_model_config_update_unknown_id_remains_404() -> None:
    response = client.put(
        "/api/v1/model-configs/00000000-0000-0000-0000-000000000000",
        json={"config": {"n_states": 3, "lookback_window": 64}},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "model config not found"


def test_model_config_route_accepts_new_model_families_with_strict_constraints() -> None:
    torch_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "torch_nn_timeseries",
            "config": {
                "task_type": "forecasting",
                "data_type": "time_series",
                "architecture": "transformer_encoder",
                "lookback_window": 96,
                "horizon_steps": 24,
                "hidden_size": 128,
                "num_layers": 2,
                "num_attention_heads": 8,
                "dropout": 0.2,
                "learning_rate": 0.0005,
                "batch_size": 64,
                "loss_function": "mse",
            },
        },
    )
    assert torch_response.status_code == 201

    kalman_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "kalman_filter",
            "config": {
                "task_type": "filtering",
                "data_type": "state_space_timeseries",
                "transition_structure": "identity",
                "state_dimension": 6,
                "observation_dimension": 6,
                "process_noise": 0.2,
                "measurement_noise": 0.1,
                "initial_covariance_scale": 1.5,
            },
        },
    )
    assert kalman_response.status_code == 201

    arima_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "arima",
            "config": {
                "task_type": "forecasting",
                "data_type": "time_series_univariate",
                "p": 2,
                "d": 1,
                "q": 1,
                "seasonal_period": 12,
                "seasonal_p": 1,
                "seasonal_d": 0,
                "seasonal_q": 1,
                "trend": "constant",
            },
        },
    )
    assert arima_response.status_code == 201


def test_model_config_route_rejects_incompatible_task_or_data_type_for_new_families() -> None:
    torch_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "torch_nn_timeseries",
            "config": {
                "task_type": "classification",
                "data_type": "tabular",
                "architecture": "lstm",
                "lookback_window": 32,
                "horizon_steps": 8,
                "hidden_size": 64,
            },
        },
    )
    assert torch_response.status_code == 422

    kalman_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "kalman_filter",
            "config": {
                "task_type": "forecasting",
                "data_type": "time_series",
                "state_dimension": 4,
                "observation_dimension": 2,
                "process_noise": 0.3,
                "measurement_noise": 0.1,
            },
        },
    )
    assert kalman_response.status_code == 422

    arima_response = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "arima",
            "config": {
                "task_type": "filtering",
                "data_type": "time_series",
                "p": 0,
                "d": 0,
                "q": 0,
            },
        },
    )
    assert arima_response.status_code == 422


def test_training_sweep_backtest_testing_routes_emit_queued_job_flow() -> None:
    dataset = client.post(
        "/api/v1/market-data/ingestions",
        json={
            "source": "test-fixture",
            "symbols": ["AAPL"],
            "timeframe": "1d",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        },
    ).json()

    model_config = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "hmm_regime_switching",
            "config": {
                "n_states": 4,
                "lookback_window": 120,
                "covariance_type": "full",
                "convergence_tol": 0.005,
                "max_iterations": 400,
            },
        },
    ).json()

    training = client.post(
        "/api/v1/training-runs",
        json={
            "model_config_id": model_config["id"],
            "dataset_id": dataset["request_id"],
            "parameters": {"epochs": 2},
            "constraints": {
                "transaction_cost": {"bps": 3.5, "per_contract_fee": 0.15},
                "slippage_buckets": [
                    {
                        "liquidity_bucket": "high",
                        "volatility_bucket": "low",
                        "slippage_bps": 1.2,
                    }
                ],
                "execution_delay": {"signal_to_fill_lag_steps": 1},
                "limits": {"max_turnover": 0.8, "max_position_abs": 0.2, "leverage_cap": 1.5},
            },
        },
    )
    assert training.status_code == 201
    training_payload = training.json()
    assert training_payload["constraints"]["transaction_cost"]["bps"] == 3.5
    assert training_payload["parameters"]["run_metadata"]["constraints"]["limits"]["leverage_cap"] == 1.5

    parameter_set = client.post(
        "/api/v1/parameter-sets",
        json={
            "model_config_id": model_config["id"],
            "name": "baseline-sweep-template",
            "parameters": {"lr": 0.001, "hidden": 64},
            "version_tag": "v1.0.0",
            "provenance_metadata": {"source_run_id": "bootstrap-run", "source_model": "hmm_regime_switching", "config_hash": "abc123"},
        },
    )
    assert parameter_set.status_code == 201
    parameter_set_payload = parameter_set.json()

    sweep = client.post(
        "/api/v1/parameter-sweeps",
        json={
            "model_config_id": model_config["id"],
            "parameter_set_id": parameter_set_payload["id"],
            "objective": "maximize_sharpe",
            "search_space": {"lr": [0.001, 0.01]},
            "provenance_snapshot": {
                "source_run_id": "bootstrap-run",
                "source_model": "hmm_regime_switching",
                "config_hash": "abc123",
                "dataset_id": dataset["request_id"],
            },
        },
    )
    assert sweep.status_code == 201
    sweep_payload = sweep.json()
    assert sweep_payload["parameter_set_id"] == parameter_set_payload["id"]
    assert sweep_payload["provenance_snapshot"]["config_hash"] == "abc123"

    backtest = client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_key": "mean_revert.v1",
            "model_config_id": model_config["id"],
            "window_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
            "window_end": datetime(2025, 12, 31, tzinfo=UTC).isoformat(),
            "parameters": {"rebalance": "1d", "dataset_id": dataset["request_id"]},
        },
    )
    assert backtest.status_code == 201

    testing_run = client.post(
        "/api/v1/testing-runs",
        json={
            "mode": "smoke",
            "target_refs": [{"target_type": "strategy", "target_id": "mean_revert.v1", "label": "MRv1"}],
            "parameters": {"max_duration_sec": 120},
        },
    )
    assert testing_run.status_code == 201
    testing_payload = testing_run.json()
    assert testing_payload["mode"] == "smoke"
    assert testing_payload["target_refs"][0]["target_type"] == "strategy"

    job_events = client.get(f"/api/v1/jobs/{training_payload['job_id']}/events")
    assert job_events.status_code == 200
    queued = job_events.json()[0]
    assert queued["status"] == "queued"
    assert queued["run_type"] == "training"
    assert queued["progress_pct"] == 0.0

    testing_events = client.get(f"/api/v1/jobs/{testing_payload['job_id']}/events")
    assert testing_events.status_code == 200
    testing_queued = testing_events.json()[0]
    assert testing_queued["run_type"] == "testing"


def test_parameter_set_clone_and_version_history_routes() -> None:
    model_config = client.post(
        "/api/v1/model-configs",
        json={
            "model_family": "hmm_regime_switching",
            "config": {
                "n_states": 3,
                "lookback_window": 100,
                "covariance_type": "diag",
                "convergence_tol": 0.01,
                "max_iterations": 300,
            },
        },
    ).json()

    created = client.post(
        "/api/v1/parameter-sets",
        json={
            "model_config_id": model_config["id"],
            "name": "seed-template",
            "parameters": {"lr": 0.001},
            "version_tag": "v1.0.0",
            "provenance_metadata": {"source_run_id": "run-1", "source_model": "seed", "config_hash": "h1"},
        },
    )
    assert created.status_code == 201
    root = created.json()

    cloned = client.post(
        f"/api/v1/parameter-sets/{root['id']}/clone",
        json={"name": "seed-template-clone", "version_tag": "v1.0.1"},
    )
    assert cloned.status_code == 201
    clone_payload = cloned.json()
    assert clone_payload["parent_set_id"] == root["id"]

    history = client.get(f"/api/v1/parameter-sets/{clone_payload['id']}/versions")
    assert history.status_code == 200
    version_payload = history.json()
    assert [item["id"] for item in version_payload] == [root["id"], clone_payload["id"]]


def test_graph_neighborhood_endpoint_filters_by_node_types() -> None:
    topology = client.get("/api/v1/graph/topology").json()
    strategy_node = next(node for node in topology["nodes"] if node["type"] == "strategy")

    response = client.post(
        "/api/v1/graph/neighborhood",
        json={"seed_node_id": strategy_node["id"], "depth": 2, "include_node_types": ["strategy", "model"]},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["seed_node_id"] == strategy_node["id"]
    assert all(node["type"] in {"strategy", "model"} for node in payload["nodes"])


def test_market_data_ingestion_endpoint_returns_contract_shape_and_persists() -> None:
    ingestion = client.post(
        "/api/v1/market-data/ingestions",
        json={
            "source": "massive",
            "symbols": ["AAPL", "MSFT"],
            "timeframe": "day",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        },
    )

    assert ingestion.status_code == 202
    payload = ingestion.json()
    assert payload["status"] == "accepted"
    assert payload["source"] == "massive"
    assert payload["symbols"] == ["AAPL", "MSFT"]

    dataset = client.get(f"/api/v1/market-data/datasets/{payload['request_id']}")
    assert dataset.status_code == 200
    assert dataset.json()["metadata"]["symbols"] == ["AAPL", "MSFT"]


def test_websocket_event_envelope_contract_schema_accepts_jobs_payload() -> None:
    envelope = WebSocketContractEnvelope.model_validate(
        {
            "seq": 1,
            "topic": "jobs",
            "timestamp": datetime.now(UTC).isoformat(),
            "payload": {
                "job_id": "11111111-1111-1111-1111-111111111111",
                "status": "queued",
                "progress_pct": 0,
                "message": "queued",
            },
        }
    )

    dumped = envelope.model_dump(mode="json")
    assert dumped["contract_name"] == "gb.ws.event"
    assert dumped["contract_version"] == "1.0"
    assert dumped["payload"]["status"] == "queued"
