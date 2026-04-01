from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_risk_override_and_recent_decisions_endpoints() -> None:
    create_override = client.post(
        "/api/v1/risk/overrides",
        json={"strategy_key": "mean_reversion", "max_quantity": 10, "created_by": "test"},
    )
    assert create_override.status_code == 201

    list_overrides = client.get("/api/v1/risk/overrides")
    assert list_overrides.status_code == 200
    assert len(list_overrides.json()) >= 1

    create_instance = client.post(
        "/api/v1/strategies/instances",
        json={
            "strategy_key": "mean_reversion",
            "mode": "paper",
            "intent": {"symbol": "AAPL", "side": "buy", "quantity": 20, "limit_price": 100},
        },
    )
    instance_id = create_instance.json()["id"]

    start_response = client.post(f"/api/v1/strategies/instances/{instance_id}/start")
    assert start_response.status_code == 403

    recent = client.get("/api/v1/risk/decisions/recent")
    assert recent.status_code == 200
    payload = recent.json()
    assert len(payload) >= 1
    assert payload[0]["reason_code"] in {"MAX_QUANTITY_EXCEEDED", "MISSING_ORDER_FIELDS", "APPROVED"}
