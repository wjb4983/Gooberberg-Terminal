from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_ingestion_supports_idempotency_and_logs() -> None:
    payload = {
        "provider": "massive",
        "asset_class": "stocks",
        "symbols": ["AAPL", "MSFT"],
        "timeframe": "1d",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "idempotency_key": "demo-key-1",
        "alias": "jan-tech-sample",
        "requested_by": "test-user",
        "freshness_sla_days": 5,
    }
    first = client.post("/api/v1/market-data/ingestions", json=payload)
    assert first.status_code == 202
    body = first.json()
    assert body["request_id"] == "demo-key-1"
    assert isinstance(body.get("logs"), list)

    second = client.post("/api/v1/market-data/ingestions", json=payload)
    assert second.status_code == 202
    assert second.json()["status"] == "already_exists"


def test_batch_preset_ingestion_endpoint() -> None:
    response = client.post(
        "/api/v1/market-data/ingestions/batch",
        json={"preset_ids": ["us_stocks_daily_core", "us_stocks_intraday_flexible"], "requested_by": "qa"},
    )
    assert response.status_code == 202
    body = response.json()
    assert len(body) == 2
    assert all("request_id" in item for item in body)
