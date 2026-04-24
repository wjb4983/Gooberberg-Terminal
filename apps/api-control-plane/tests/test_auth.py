import os

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


TOKEN_ENV = "GB_API_AUTH_TOKEN"
SCOPE_ENV = "GB_API_AUTH_SCOPE"


def _reset_settings() -> None:
    get_settings.cache_clear()


def test_non_health_endpoint_rejects_missing_token() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    os.environ[SCOPE_ENV] = "control-plane:admin"
    _reset_settings()

    try:
        client = TestClient(create_app())

        response = client.get("/api/v1/models/deployments")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["scope"] == "control-plane:admin"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token

        if previous_scope is None:
            os.environ.pop(SCOPE_ENV, None)
        else:
            os.environ[SCOPE_ENV] = previous_scope

        _reset_settings()


def test_read_only_endpoint_accepts_read_scope() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    os.environ[SCOPE_ENV] = "control-plane:read"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get(
            "/api/v1/models/deployments",
            headers={"Authorization": "Bearer private-token"},
        )

        assert response.status_code == 200
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token

        if previous_scope is None:
            os.environ.pop(SCOPE_ENV, None)
        else:
            os.environ[SCOPE_ENV] = previous_scope

        _reset_settings()


def test_mutating_endpoint_rejects_read_only_scope() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    os.environ[SCOPE_ENV] = "control-plane:read"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/v1/jobs",
            headers={"Authorization": "Bearer private-token"},
            json={"job_type": "training", "payload": {}},
        )

        assert response.status_code == 403
        body = response.json()
        assert body["required_scope"] == "control-plane:write"
        assert body["granted_scope"] == "control-plane:read"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token

        if previous_scope is None:
            os.environ.pop(SCOPE_ENV, None)
        else:
            os.environ[SCOPE_ENV] = previous_scope

        _reset_settings()


def test_health_endpoint_stays_public() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        queue_response = client.get("/api/v1/health/queue")
        assert queue_response.status_code == 200
        liveness_response = client.get("/healthz")
        assert liveness_response.status_code == 200
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_non_health_root_endpoint_requires_token_when_enabled() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get("/")
        assert response.status_code == 401
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()
