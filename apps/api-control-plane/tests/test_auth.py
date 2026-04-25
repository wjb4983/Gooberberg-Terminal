import os

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


TOKEN_ENV = "GB_API_AUTH_TOKEN"
SCOPE_ENV = "GB_API_AUTH_SCOPE"
TOKENS_ENV = "GB_API_AUTH_TOKENS"
REVOKED_ENV = "GB_API_AUTH_REVOKED_TOKEN_IDS"


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
        assert response.json()["auth_result"] == "missing_header"
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


def test_model_config_mutation_requires_admin_scope() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    os.environ[SCOPE_ENV] = "control-plane:write"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/v1/model-configs",
            headers={"Authorization": "Bearer private-token"},
            json={"model_family": "arima", "config": {"p": 1, "d": 1, "q": 1}},
        )

        assert response.status_code == 403
        body = response.json()
        assert body["required_scope"] == "control-plane:admin"
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


def test_cors_preflight_bypasses_bearer_auth() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    os.environ[TOKEN_ENV] = "private-token"
    os.environ[SCOPE_ENV] = "control-plane:admin"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.options(
            "/api/v1/model-configs",
            headers={
                "Origin": "http://localhost:1420",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:1420"

        packaged_response = client.options(
            "/api/v1/model-configs",
            headers={
                "Origin": "http://tauri.localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert packaged_response.status_code == 200
        assert packaged_response.headers["access-control-allow-origin"] == "http://tauri.localhost"
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


def test_dual_accept_mode_accepts_structured_tokens_and_sets_header() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    previous_scope = os.environ.get(SCOPE_ENV)
    previous_tokens = os.environ.get(TOKENS_ENV)
    os.environ.pop(TOKEN_ENV, None)
    os.environ.pop(SCOPE_ENV, None)
    os.environ[TOKENS_ENV] = (
        "token-a|first-secret|control-plane:read|2099-01-01T00:00:00Z;"
        "token-b|second-secret|control-plane:read,control-plane:write|2099-01-01T00:00:00Z"
    )
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get(
            "/api/v1/models/deployments",
            headers={"Authorization": "Bearer first-secret"},
        )
        assert response.status_code == 200
        assert response.headers["x-auth-token-mode"] == "dual-accept"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        if previous_scope is None:
            os.environ.pop(SCOPE_ENV, None)
        else:
            os.environ[SCOPE_ENV] = previous_scope
        if previous_tokens is None:
            os.environ.pop(TOKENS_ENV, None)
        else:
            os.environ[TOKENS_ENV] = previous_tokens
        _reset_settings()


def test_expired_structured_token_requires_reauthentication() -> None:
    previous_tokens = os.environ.get(TOKENS_ENV)
    os.environ[TOKENS_ENV] = "expired|expired-secret|control-plane:full|2000-01-01T00:00:00Z"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get(
            "/api/v1/models/deployments",
            headers={"Authorization": "Bearer expired-secret"},
        )
        assert response.status_code == 401
        assert response.json()["auth_result"] == "expired_token"
    finally:
        if previous_tokens is None:
            os.environ.pop(TOKENS_ENV, None)
        else:
            os.environ[TOKENS_ENV] = previous_tokens
        _reset_settings()


def test_revoked_structured_token_is_rejected() -> None:
    previous_tokens = os.environ.get(TOKENS_ENV)
    previous_revoked = os.environ.get(REVOKED_ENV)
    os.environ[TOKENS_ENV] = "revoke-me|active-secret|control-plane:full|2099-01-01T00:00:00Z"
    os.environ[REVOKED_ENV] = "revoke-me"
    _reset_settings()

    try:
        client = TestClient(create_app())
        response = client.get(
            "/api/v1/models/deployments",
            headers={"Authorization": "Bearer active-secret"},
        )
        assert response.status_code == 401
        assert response.json()["auth_result"] == "revoked_token"
    finally:
        if previous_tokens is None:
            os.environ.pop(TOKENS_ENV, None)
        else:
            os.environ[TOKENS_ENV] = previous_tokens
        if previous_revoked is None:
            os.environ.pop(REVOKED_ENV, None)
        else:
            os.environ[REVOKED_ENV] = previous_revoked
        _reset_settings()
