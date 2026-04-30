from fastapi.testclient import TestClient

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.api.routers.alerts import _alert_lifecycle_store, _alert_store
from app.main import create_app


client = TestClient(create_app())


def setup_function() -> None:
    _alert_store.clear()
    _alert_lifecycle_store.clear()


def test_get_alerts_returns_seeded_alerts() -> None:
    response = client.get('/api/v1/alerts')
    assert response.status_code == 200

    payload = response.json()
    assert len(payload) >= 2
    first = payload[0]
    assert first['service']
    assert first['level'] in {'info', 'warning', 'critical'}
    assert first['trace_id']
    assert first['message']


def test_ack_alert_changes_status() -> None:
    alerts_response = client.get('/api/v1/alerts')
    alert_id = alerts_response.json()[0]['id']

    ack_response = client.post(f'/api/v1/alerts/{alert_id}/ack')
    assert ack_response.status_code == 200
    payload = ack_response.json()
    assert payload['alert']['id'] == alert_id
    assert payload['alert']['status'] == 'acknowledged'
    assert payload['alert']['acknowledged_at'] is not None

    second_ack = client.post(f'/api/v1/alerts/{alert_id}/ack')
    assert second_ack.status_code == 409


def test_emit_alert_routes_and_persists_lifecycle() -> None:
    payload = {
        "service": "service-risk-exec",
        "level": "critical",
        "trace_id": "trace-manual-emit",
        "message": "Critical check failed.",
        "category": "risk",
    }
    response = client.post("/api/v1/alerts/emit", json=payload)
    assert response.status_code == 201
    alert_id = response.json()["id"]

    lifecycle = client.get(f"/api/v1/alerts/{alert_id}/lifecycle")
    assert lifecycle.status_code == 200
    event_types = [entry["event_type"] for entry in lifecycle.json()]
    assert "triggered" in event_types


def test_critical_alert_escalates_when_unresolved() -> None:
    alerts_response = client.get("/api/v1/alerts")
    critical = next(item for item in alerts_response.json() if item["level"] == "critical")
    alert = _alert_store[UUID(critical["id"])]
    alert.timestamp = datetime.now(UTC) - timedelta(minutes=16)

    refreshed = client.get("/api/v1/alerts")
    assert refreshed.status_code == 200
    updated = next(item for item in refreshed.json() if item["id"] == critical["id"])
    assert updated["status"] == "escalated"
