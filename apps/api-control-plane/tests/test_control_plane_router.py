from fastapi.testclient import TestClient

from app.main import create_app


def test_external_status_returns_not_connected_when_unconfigured() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get('/api/v1/control-plane/services/external-status')

    assert response.status_code == 200
    payload = response.json()
    assert payload['paper']['status'] == 'not_connected'
    assert payload['live']['status'] == 'not_connected'


def test_model_leaderboard_returns_ranked_entries() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get('/api/v1/control-plane/models/leaderboard')

    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert payload[0]['rank'] == 1
    assert payload[0]['score'] >= payload[-1]['score']
