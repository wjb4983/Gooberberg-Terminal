from fastapi.testclient import TestClient

from app.api.routers.alerts import _alert_store
from app.main import create_app


client = TestClient(create_app())


def setup_function() -> None:
    _alert_store.clear()


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
