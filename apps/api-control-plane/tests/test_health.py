from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_health_endpoint_returns_placeholder_dependency_status() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "gooberberg-api-control-plane"
    assert payload["postgres"]["detail"].startswith("placeholder")
    assert payload["redis"]["detail"].startswith("placeholder")


def test_healthz_endpoint_returns_ok() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

