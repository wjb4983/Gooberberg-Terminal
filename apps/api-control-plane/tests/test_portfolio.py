from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_portfolio_snapshot_endpoint_returns_snapshot_schema() -> None:
    response = client.get("/api/v1/portfolio/snapshot")
    assert response.status_code == 200

    payload = response.json()
    assert payload["account_id"]
    assert isinstance(payload["positions"], list)
    assert "gross_exposure" in payload
    assert "net_exposure" in payload
    assert "unrealized_pnl" in payload
