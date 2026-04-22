from fastapi.testclient import TestClient

from app.main import create_app


def test_backtest_preflight_returns_estimate() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/backtest-runs/preflight",
            json={
                "strategy_key": "mean_reversion",
                "model_config_id": None,
                "window_start": "2024-01-01T00:00:00Z",
                "window_end": "2024-12-31T00:00:00Z",
                "parameters": {"symbols": ["AAPL", "MSFT", "NVDA"]},
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol_count"] == 3
    assert payload["estimated_units"] > 0


def test_backtest_create_requires_confirmation_for_large_runs() -> None:
    with TestClient(create_app()) as client:
        create_response = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "window_start": "2020-01-01T00:00:00Z",
                "window_end": "2025-12-31T00:00:00Z",
                "parameters": {"symbols": ["AAPL", "MSFT"]},
            },
        )
        assert create_response.status_code == 409

        preflight = client.post(
            "/api/v1/backtest-runs/preflight",
            json={
                "strategy_key": "mean_reversion",
                "window_start": "2020-01-01T00:00:00Z",
                "window_end": "2025-12-31T00:00:00Z",
                "parameters": {"symbols": ["AAPL", "MSFT"]},
            },
        )
        token = preflight.json()["confirmation_token"]

        confirmed = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "window_start": "2020-01-01T00:00:00Z",
                "window_end": "2025-12-31T00:00:00Z",
                "parameters": {"symbols": ["AAPL", "MSFT"]},
                "confirmation_token": token,
            },
        )
        assert confirmed.status_code == 201
