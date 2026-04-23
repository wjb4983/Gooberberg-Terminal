from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_model_deployment_lifecycle_scaffold() -> None:
    create_response = client.post(
        "/api/v1/models/deployments",
        json={
            "model_name": "risk-bert",
            "model_version": "2026.04.01",
            "artifact_ref": "s3://gooberberg/models/risk-bert/2026.04.01/model.tar.gz",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["status"] == "deploying"

    deployment_id = created["id"]

    list_response = client.get("/api/v1/models/deployments")
    assert list_response.status_code == 200
    assert any(item["id"] == deployment_id for item in list_response.json())

    activate_response = client.post(f"/api/v1/models/deployments/{deployment_id}/activate")
    assert activate_response.status_code == 200
    activated = activate_response.json()
    assert activated["deployment"]["status"] == "active"

    duplicate_activate = client.post(f"/api/v1/models/deployments/{deployment_id}/activate")
    assert duplicate_activate.status_code == 409

    deactivate_response = client.post(f"/api/v1/models/deployments/{deployment_id}/deactivate")
    assert deactivate_response.status_code == 200
    deactivated = deactivate_response.json()
    assert deactivated["deployment"]["status"] == "inactive"

    duplicate_deactivate = client.post(f"/api/v1/models/deployments/{deployment_id}/deactivate")
    assert duplicate_deactivate.status_code == 409


def test_model_deployment_validates_fields() -> None:
    response = client.post(
        "/api/v1/models/deployments",
        json={
            "model_name": "",
            "model_version": "",
            "artifact_ref": "??",
        },
    )

    assert response.status_code == 422


def test_model_families_exposes_all_registered_specs() -> None:
    response = client.get("/api/v1/models/deployments/families")
    assert response.status_code == 200
    payload = response.json()
    assert "hmm_regime_switching" in payload
    assert "torch_nn_timeseries" in payload
    assert "kalman_filter" in payload
    assert "arima" in payload
