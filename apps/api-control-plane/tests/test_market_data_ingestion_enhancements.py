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


def test_list_ingestions_returns_most_recent_first_with_dataset_and_request_ids() -> None:
    first = client.post(
        "/api/v1/market-data/ingestions",
        json={
            "provider": "massive",
            "asset_class": "stocks",
            "symbols": ["SPY"],
            "timeframe": "1d",
            "start_date": "2024-01-01",
            "end_date": "2024-01-10",
            "idempotency_key": "list-ingestion-first",
            "alias": "first-alias",
            "requested_by": "test-user",
        },
    )
    assert first.status_code == 202

    second = client.post(
        "/api/v1/market-data/ingestions",
        json={
            "provider": "massive",
            "asset_class": "stocks",
            "symbols": ["QQQ"],
            "timeframe": "1d",
            "start_date": "2024-02-01",
            "end_date": "2024-02-10",
            "idempotency_key": "list-ingestion-second",
            "alias": "second-alias",
            "requested_by": "test-user",
        },
    )
    assert second.status_code == 202
    second_payload = second.json()

    listed = client.get("/api/v1/market-data/ingestions")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) >= 2
    assert body[0]["request_id"] == "list-ingestion-second"
    assert body[0]["dataset_id"] == second_payload["dataset_id"]
    assert body[0]["effective_params"]["alias"] == "second-alias"


def test_provider_capabilities_exposes_minimum_fetch_interval_policy() -> None:
    response = client.get("/api/v1/market-data/provider-capabilities")
    assert response.status_code == 200
    body = response.json()
    massive_stocks = next(item for item in body if item["provider"] == "massive" and item["asset_class"] == "stocks")
    assert massive_stocks["minimum_fetch_interval"] == "1 minute"
    assert massive_stocks["provider_native_subminute_supported"] is False
