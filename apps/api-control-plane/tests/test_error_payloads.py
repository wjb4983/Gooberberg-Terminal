from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

TOKEN_ENV = "GB_API_AUTH_TOKEN"


def _reset_settings() -> None:
    get_settings.cache_clear()


def _assert_error_shape(payload: dict[str, object], *, status: int) -> None:
    assert payload["status"] == status
    assert isinstance(payload["request_id"], str)
    assert payload["request_id"]
    assert isinstance(payload["error_code"], str)
    assert payload["error_code"]
    assert isinstance(payload["detail"], str)
    assert payload["detail"]


def test_missing_and_invalid_token_errors_have_deterministic_shape() -> None:
    previous_token = os.environ.get(TOKEN_ENV)
    os.environ[TOKEN_ENV] = "expected-token"
    _reset_settings()

    try:
        with TestClient(create_app()) as client:
            missing = client.get("/api/v1/model-configs")
            assert missing.status_code == 401
            _assert_error_shape(missing.json(), status=401)
            assert missing.json()["error_code"] == "http_401"
            assert missing.json()["detail"] == "Unauthorized"

            invalid = client.get("/api/v1/model-configs", headers={"Authorization": "Bearer wrong-token"})
            assert invalid.status_code == 401
            _assert_error_shape(invalid.json(), status=401)
            assert invalid.json()["error_code"] == "http_401"
            assert invalid.json()["detail"] == "Unauthorized"
    finally:
        if previous_token is None:
            os.environ.pop(TOKEN_ENV, None)
        else:
            os.environ[TOKEN_ENV] = previous_token
        _reset_settings()


def test_404_errors_include_deterministic_shape_for_unknown_family_and_model_config_id() -> None:
    with TestClient(create_app()) as client:
        unknown_family = client.post(
            "/api/v1/model-configs",
            json={"model_family": "unknown_family", "config": {"anything": "goes"}},
        )
        assert unknown_family.status_code == 404
        _assert_error_shape(unknown_family.json(), status=404)
        assert unknown_family.json()["detail"] == "POST /api/v1/model-configs: unknown model_family='unknown_family'"

        unknown_model_config = client.get("/api/v1/model-configs/00000000-0000-0000-0000-000000000000")
        assert unknown_model_config.status_code == 404
        _assert_error_shape(unknown_model_config.json(), status=404)
        assert unknown_model_config.json()["detail"] == "model config not found"


def test_422_and_400_errors_include_deterministic_shape() -> None:
    with TestClient(create_app()) as client:
        invalid_payload = client.post(
            "/api/v1/model-configs",
            json={"model_family": "hmm_regime_switching", "config": {"n_states": "not-int"}},
        )
        assert invalid_payload.status_code == 422
        _assert_error_shape(invalid_payload.json(), status=422)
        assert "invalid config payload" in invalid_payload.json()["detail"]

        invalid_request_schema = client.post("/api/v1/model-configs", json={"config": {"n_states": 3}})
        assert invalid_request_schema.status_code == 422
        _assert_error_shape(invalid_request_schema.json(), status=422)
        assert invalid_request_schema.json()["error_code"] == "validation_error"

        bad_job = client.post("/api/v1/jobs", json={"job_type": "unknown_task", "payload": {}})
        assert bad_job.status_code == 400
        _assert_error_shape(bad_job.json(), status=400)
        assert "task type is not registered" in bad_job.json()["detail"]


def test_model_config_domain_errors_do_not_regress_to_generic_500() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/model-configs",
            json={
                "model_family": "arima",
                "config": {"task_type": "forecasting", "data_type": "time_series_univariate", "p": "x", "d": 1, "q": 1},
            },
        )

    assert response.status_code == 422
    body = response.json()
    _assert_error_shape(body, status=422)
    assert body["error_code"] != "internal_error"
