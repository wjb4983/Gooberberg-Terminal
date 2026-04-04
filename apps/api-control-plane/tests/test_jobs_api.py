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
