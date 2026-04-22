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


def test_queue_health_endpoint_reports_degraded_without_queue_backend() -> None:
    response = client.get("/api/v1/health/queue")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["queue_depth"] is None


def test_queue_worker_heartbeat_updates_timestamp() -> None:
    heartbeat_response = client.post("/api/v1/health/queue/heartbeat")
    assert heartbeat_response.status_code == 200

    queue_response = client.get("/api/v1/health/queue")
    assert queue_response.status_code == 200
    payload = queue_response.json()
    assert payload["worker_heartbeat_at"] is not None
