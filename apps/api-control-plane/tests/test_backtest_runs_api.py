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


def test_backtest_replay_validation_detects_divergence() -> None:
    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "window_start": "2024-01-01T00:00:00Z",
                "window_end": "2024-01-02T00:00:00Z",
                "git_sha": "strategy-v1",
                "parameters": {},
            },
        )
        assert created.status_code == 201
        run = created.json()

        response = client.post(
            f"/api/v1/backtest-runs/{run['id']}/replay-validation",
            json={
                "strategy_version": "strategy-v1",
                "config_hash": run["config_hash"],
                "events": [
                    {"type": "decision", "metadata": {"signal": "buy"}},
                    {
                        "type": "order",
                        "order_id": "o-1",
                        "symbol": "AAPL",
                        "side": "buy",
                        "quantity": 10,
                        "price": 100,
                    },
                    {
                        "type": "fill",
                        "order_id": "o-1",
                        "symbol": "AAPL",
                        "quantity": 10,
                        "price": 101,
                        "fee": 1,
                    },
                ],
                "expected_outcomes": {
                    "decisions": [],
                    "orders": [],
                    "positions": [],
                    "pnl_state": {},
                },
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["pinning"]["matches"] is True
    assert payload["validation"]["status"] == "diverged"
    assert payload["validation"]["mismatch_count"] >= 1
