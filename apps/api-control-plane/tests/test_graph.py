from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_graph_topology_endpoint_returns_mock_nodes_and_edges() -> None:
    response = client.get('/api/v1/graph/topology')
    assert response.status_code == 200

    payload = response.json()
    assert len(payload['nodes']) >= 100
    assert len(payload['edges']) >= 99
    assert payload['nodes'][0]['type'] in {
        'strategy',
        'model',
        'data_source',
        'risk_rule',
        'execution_adapter',
        'job',
    }
