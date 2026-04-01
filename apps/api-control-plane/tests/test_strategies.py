from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_strategy_instance_mocked_lifecycle() -> None:
    create_response = client.post(
        "/api/v1/strategies/instances",
        json={
            "strategy_key": "mean_reversion",
            "mode": "paper",
            "intent": {"notes": "placeholder intent", "params": {"window": 20}},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["mode"] == "paper"
    assert created["status"] == "created"

    instance_id = created["id"]

    list_response = client.get("/api/v1/strategies/instances")
    assert list_response.status_code == 200
    assert any(item["id"] == instance_id for item in list_response.json())

    start_response = client.post(f"/api/v1/strategies/instances/{instance_id}/start")
    assert start_response.status_code == 200
    started = start_response.json()
    assert started["instance"]["status"] == "running"
    assert started["instance"]["started_at"] is not None

    invalid_start_response = client.post(f"/api/v1/strategies/instances/{instance_id}/start")
    assert invalid_start_response.status_code == 409

    stop_response = client.post(f"/api/v1/strategies/instances/{instance_id}/stop")
    assert stop_response.status_code == 200
    stopped = stop_response.json()
    assert stopped["instance"]["status"] == "stopped"
    assert stopped["instance"]["stopped_at"] is not None

    invalid_stop_response = client.post(f"/api/v1/strategies/instances/{instance_id}/stop")
    assert invalid_stop_response.status_code == 409


def test_strategy_instance_requires_valid_mode() -> None:
    response = client.post(
        "/api/v1/strategies/instances",
        json={"strategy_key": "breakout", "mode": "demo"},
    )
    assert response.status_code == 422
