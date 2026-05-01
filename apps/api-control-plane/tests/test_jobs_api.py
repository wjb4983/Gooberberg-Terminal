import os

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

TOKEN_ENV = "GB_API_AUTH_TOKEN"


def _reset_settings() -> None:
    get_settings.cache_clear()


def test_health_endpoint_is_public_even_when_auth_enabled() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = "test-token"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_jobs_route_requires_auth_when_token_configured() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = "test-token"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.post("/api/v1/jobs", json={"job_type": "demo", "payload": {}})

        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_job_create_and_get_round_trip() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ.pop(TOKEN_ENV, None)
    _reset_settings()

    try:
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/api/v1/jobs",
                json={"job_type": "backtest", "payload": {"symbol": "SPY"}},
            )
            assert create_response.status_code == 202

            created = create_response.json()
            assert created["job_type"] == "backtest"
            assert created["status"] == "queued"
            assert created["payload"] == {"symbol": "SPY"}

            get_response = client.get(f"/api/v1/jobs/{created['id']}")
            assert get_response.status_code == 200

            fetched = get_response.json()
            assert fetched["id"] == created["id"]
            assert fetched["status"] == "queued"
            assert fetched["detail"] == "job accepted by api-control-plane"
            assert fetched["trace_id"] == created["trace_id"]
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_job_create_requires_registered_task_type() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ.pop(TOKEN_ENV, None)
    _reset_settings()

    try:
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/api/v1/jobs",
                json={"job_type": "unknown_task", "payload": {"symbol": "SPY"}},
            )
            assert create_response.status_code == 400
            assert "task type is not registered" in create_response.json()["detail"]
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_job_artifact_manifest_summary_and_detail_routes() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ.pop(TOKEN_ENV, None)
    _reset_settings()

    try:
        with TestClient(create_app()) as client:
            create_response = client.post(
                "/api/v1/jobs",
                json={"job_type": "training", "payload": {"dataset_id": "equities_daily_v1"}},
            )
            assert create_response.status_code == 202
            created = create_response.json()

            update_response = client.post(
                f"/api/v1/jobs/{created['id']}/events",
                json={
                    "status": "success",
                    "detail": "training run completed",
                    "progress_pct": 100,
                    "message": "done",
                    "result_ref": "s3://gooberberg/runs/2026-04-23/model.tar.gz",
                    "metrics": {"best_metric": 0.9132, "loss": 0.12},
                    "artifact_checksum": "sha256:abcd1234efef5678",
                    "artifact_size_bytes": 1048576,
                    "artifact_retention_class": "intermediate",
                },
            )
            assert update_response.status_code == 200

            list_response = client.get(f"/api/v1/jobs/{created['id']}/artifacts")
            assert list_response.status_code == 200
            artifacts = list_response.json()
            assert len(artifacts) == 1
            assert artifacts[0]["artifact_ref"] == "s3://gooberberg/runs/2026-04-23/model.tar.gz"
            assert artifacts[0]["checksum"] == "sha256:abcd1234efef5678"
            assert artifacts[0]["size_bytes"] == 1048576
            assert artifacts[0]["best_metric"] == 0.9132

            detail_response = client.get(f"/api/v1/jobs/{created['id']}/artifacts/{artifacts[0]['id']}")
            assert detail_response.status_code == 200
            detail = detail_response.json()
            assert detail["metrics"]["loss"] == 0.12
            assert detail["retention_class"] == "intermediate"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_training_run_constraints_are_applied_to_artifact_metrics() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ.pop(TOKEN_ENV, None)
    _reset_settings()

    try:
        with TestClient(create_app()) as client:
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
                    "model_family": "arima",
                    "config": {
                        "task_type": "forecasting",
                        "data_type": "time_series_univariate",
                        "p": 1,
                        "d": 1,
                        "q": 1,
                    },
                },
            ).json()

            training = client.post(
                "/api/v1/training-runs",
                json={
                    "model_config_id": model_config["id"],
                    "dataset_id": dataset["request_id"],
                    "parameters": {"epochs": 1},
                    "constraints": {
                        "transaction_cost": {"bps": 4.0, "per_contract_fee": 0.0},
                        "slippage_buckets": [
                            {
                                "liquidity_bucket": "high",
                                "volatility_bucket": "low",
                                "slippage_bps": 2.0,
                            }
                        ],
                        "execution_delay": {"signal_to_fill_lag_steps": 2},
                        "limits": {"max_turnover": 1.0, "max_position_abs": 0.3, "leverage_cap": 1.5},
                    },
                },
            )
            assert training.status_code == 201
            run = training.json()

            update_response = client.post(
                f"/api/v1/jobs/{run['job_id']}/events",
                json={
                    "status": "success",
                    "detail": "training run completed",
                    "progress_pct": 100,
                    "message": "done",
                    "result_ref": "s3://gooberberg/runs/2026-04-24/model-with-constraints.tar.gz",
                    "metrics": {
                        "objective_raw": 1.0,
                        "validation_metrics": {"sharpe": 1.2},
                        "liquidity_bucket": "high",
                        "volatility_bucket": "low",
                        "turnover": 0.9,
                    },
                    "artifact_checksum": "sha256:cccc1234efef5678",
                    "artifact_size_bytes": 1024,
                    "artifact_retention_class": "intermediate",
                },
            )
            assert update_response.status_code == 200

            artifacts = client.get(f"/api/v1/jobs/{run['job_id']}/artifacts").json()
            detail = client.get(f"/api/v1/jobs/{run['job_id']}/artifacts/{artifacts[0]['id']}").json()
            assert detail["metrics"]["constraints"]["transaction_cost"]["bps"] == 4.0
            assert detail["metrics"]["constraint_penalties"]["total_bps"] == 8.0
            assert detail["metrics"]["objective_constrained"] == 0.9992
            assert detail["metrics"]["constraint_penalties"]["limit_breaches"]["max_turnover"] is False
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_success_gate_forces_failed_status_when_mandatory_artifact_missing() -> None:
    with TestClient(create_app()) as client:
        dataset = client.post(
            "/api/v1/market-data/ingestions",
            json={"source": "test-fixture", "symbols": ["AAPL"], "timeframe": "1d", "start_date": "2025-01-01", "end_date": "2025-12-31"},
        ).json()
        model_config = client.post(
            "/api/v1/model-configs",
            json={"model_family": "arima", "config": {"task_type": "forecasting", "data_type": "time_series_univariate", "p": 1, "d": 1, "q": 1}},
        ).json()
        run = client.post(
            "/api/v1/training-runs",
            json={"model_config_id": model_config["id"], "dataset_id": dataset["request_id"], "parameters": {"epochs": 1, "run_metadata": {"seed": 7}}},
        ).json()
        client.post(f"/api/v1/jobs/{run['job_id']}/events", json={"status": "running", "detail": "running"})
        response = client.post(
            f"/api/v1/jobs/{run['job_id']}/events",
            json={
                "status": "success",
                "detail": "done",
                "lineage": {"lineage_id": "abc", "dataset_fingerprint": "d1", "code_hash": "c1", "config_digest": "g1", "seed": 7},
                "artifact_manifest": [{"role": "trained_model", "sha256": "a" * 64, "size_bytes": 10}],
                "result_ref": "s3://artifact",
                "artifact_checksum": "sha256:abcd1234efef5678",
                "artifact_size_bytes": 12,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert "success gate failed" in response.json()["detail"]


def test_runs_lineage_artifacts_and_replay_endpoints() -> None:
    with TestClient(create_app()) as client:
        dataset = client.post(
            "/api/v1/market-data/ingestions",
            json={"source": "test-fixture", "symbols": ["AAPL"], "timeframe": "1d", "start_date": "2025-01-01", "end_date": "2025-12-31"},
        ).json()
        model_config = client.post(
            "/api/v1/model-configs",
            json={"model_family": "arima", "config": {"task_type": "forecasting", "data_type": "time_series_univariate", "p": 1, "d": 1, "q": 1}},
        ).json()
        run = client.post(
            "/api/v1/training-runs",
            json={
                "model_config_id": model_config["id"],
                "dataset_id": dataset["request_id"],
                "parameters": {"epochs": 1},
                "lineage": {"lineage_id": "ln-1", "dataset_fingerprint": "data-v1", "code_hash": "a" * 40, "config_digest": "cfg-v1", "seed": 7},
            },
        ).json()
        client.post(
            f"/api/v1/jobs/{run['job_id']}/events",
            json={
                "status": "success",
                "detail": "training run completed",
                "progress_pct": 100,
                "message": "done",
                "result_ref": "s3://gooberberg/runs/model.tar.gz",
                "artifact_checksum": "sha256:aaaa1234bbbb5678",
                "artifact_size_bytes": 128,
                "artifact_manifest": [{"role": "trained_model", "artifact_ref": "s3://gooberberg/runs/model.tar.gz", "checksum": "sha256:aaaa1234bbbb5678", "size_bytes": 128}],
                "lineage": {"lineage_id": "ln-1", "dataset_fingerprint": "data-v1", "code_hash": "a" * 40, "config_digest": "cfg-v1", "seed": 7},
            },
        )

        lineage_response = client.get(f"/api/v1/runs/{run['id']}/lineage")
        assert lineage_response.status_code == 200
        assert lineage_response.json()["schema_version"] == "v1"
        assert lineage_response.json()["lineage"]["dataset_fingerprint"] == "data-v1"

        artifacts_response = client.get(f"/api/v1/runs/{run['id']}/artifacts")
        assert artifacts_response.status_code == 200
        assert len(artifacts_response.json()["manifest_entries"]) >= 1
        assert artifacts_response.json()["integrity_metadata"][0]["checksum"] == "sha256:aaaa1234bbbb5678"

        replay_response = client.get(f"/api/v1/runs/{run['id']}/replay")
        assert replay_response.status_code == 200
        replay_payload = replay_response.json()
        assert replay_payload["replay_bundle"]["dataset_reference"] == dataset["request_id"]
        assert replay_payload["replay_bundle"]["seed"] == 7


def test_success_gate_allows_success_with_valid_backtest_manifest_and_seed() -> None:
    with TestClient(create_app()) as client:
        backtest = client.post(
            "/api/v1/backtest-runs",
            json={
                "strategy_key": "mean_reversion",
                "window_start": "2025-01-01T00:00:00Z",
                "window_end": "2025-01-31T00:00:00Z",
                "parameters": {"run_metadata": {"seed": 11}},
                "random_seed": 11,
            },
        ).json()
        response = client.post(
            f"/api/v1/jobs/{backtest['job_id']}/events",
            json={
                "status": "success",
                "detail": "done",
                "lineage": {"lineage_id": "xyz", "dataset_fingerprint": "d1", "code_hash": "c1", "config_digest": "g1", "seed": 11},
                "artifact_manifest": [
                    {"role": "backtest_metrics", "sha256": "b" * 64, "size_bytes": 100},
                    {"role": "trade_log", "sha256": "c" * 64, "size_bytes": 100},
                    {"role": "run_metadata", "sha256": "d" * 64, "size_bytes": 100},
                ],
                "runtime_observed": {"rows": 10},
                "expected_runtime": {"rows": 10},
                "result_ref": "s3://artifact",
                "artifact_checksum": "sha256:abcd1234efef5678",
                "artifact_size_bytes": 12,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"


def test_success_gate_blocks_final_candidate_without_required_metadata() -> None:
    with TestClient(create_app()) as client:
        dataset = client.post(
            "/api/v1/market-data/ingestions",
            json={"source": "test-fixture", "symbols": ["AAPL"], "timeframe": "1d", "start_date": "2025-01-01", "end_date": "2025-12-31"},
        ).json()
        model_config = client.post(
            "/api/v1/model-configs",
            json={"model_family": "arima", "config": {"task_type": "forecasting", "data_type": "time_series_univariate", "p": 1, "d": 1, "q": 1}},
        ).json()
        run = client.post(
            "/api/v1/training-runs",
            json={"model_config_id": model_config["id"], "dataset_id": dataset["request_id"], "parameters": {"epochs": 1, "run_metadata": {"seed": 7}}},
        ).json()
        response = client.post(
            f"/api/v1/jobs/{run['job_id']}/events",
            json={
                "status": "success",
                "detail": "done",
                "lineage": {"lineage_id": "abc", "dataset_fingerprint": "d1", "code_hash": "c1", "config_digest": "g1", "seed": 7},
                "artifact_manifest": [
                    {"role": "trained_model", "sha256": "a" * 64, "size_bytes": 10, "promotion_status": "final_candidate"},
                    {"role": "training_metrics", "sha256": "b" * 64, "size_bytes": 10, "promotion_status": "final_candidate"},
                    {"role": "run_metadata", "sha256": "c" * 64, "size_bytes": 10, "promotion_status": "final_candidate"},
                ],
                "result_ref": "s3://artifact",
                "artifact_checksum": "sha256:abcd1234efef5678",
                "artifact_size_bytes": 12,
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert "required run_metadata fields" in response.json()["detail"]
