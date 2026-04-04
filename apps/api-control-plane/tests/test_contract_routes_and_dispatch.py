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


def test_training_sweep_backtest_routes_emit_queued_job_flow() -> None:
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
            "dataset_id": "dataset://bars/aapl/day",
            "parameters": {"epochs": 2},
        },
    )
    assert training.status_code == 201
    training_payload = training.json()

    sweep = client.post(
        "/api/v1/parameter-sweeps",
        json={
            "model_config_id": model_config["id"],
            "objective": "maximize_sharpe",
            "search_space": {"lr": [0.001, 0.01]},
        },
    )
    assert sweep.status_code == 201

    backtest = client.post(
        "/api/v1/backtest-runs",
        json={
            "strategy_key": "mean_revert.v1",
            "model_config_id": model_config["id"],
            "window_start": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
            "window_end": datetime(2025, 12, 31, tzinfo=UTC).isoformat(),
            "parameters": {"rebalance": "1d"},
        },
    )
    assert backtest.status_code == 201

    job_events = client.get(f"/api/v1/jobs/{training_payload['job_id']}/events")
    assert job_events.status_code == 200
    queued = job_events.json()[0]
    assert queued["status"] == "queued"
    assert queued["run_type"] == "training"
    assert queued["progress_pct"] == 0.0


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
