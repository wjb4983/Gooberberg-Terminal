from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def test_audit_entity_endpoints_include_required_metadata() -> None:
    decision_id = uuid4()
    response = client.get(f"/api/v1/audit/decisions/{decision_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(decision_id)
    assert payload["lineage_links"]
    assert payload["provenance"]["config_digest"].startswith("sha256:")
    assert payload["risk_outcome"]["decision"]
    assert payload["execution"]["total_latency_ms"] >= 0
    assert payload["observed_at"]

    order_response = client.get(f"/api/v1/audit/orders/{uuid4()}")
    fill_response = client.get(f"/api/v1/audit/fills/{uuid4()}")
    trace_response = client.get(f"/api/v1/audit/traces/{uuid4()}")
    assert order_response.status_code == 200
    assert fill_response.status_code == 200
    assert trace_response.status_code == 200


def test_audit_events_and_replay_endpoints() -> None:
    events_response = client.get("/api/v1/audit/events", params={"filters": "strategy:mean-reversion-alpha"})
    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert events_payload["filters"] == "strategy:mean-reversion-alpha"
    assert len(events_payload["events"]) == 1

    replay_response = client.get("/api/v1/audit/replay", params={"trace_id": str(uuid4())})
    assert replay_response.status_code == 200
    replay_payload = replay_response.json()
    assert replay_payload["lineage_links"]
    assert replay_payload["provenance"]["strategy_version"]
    assert replay_payload["risk_outcome"]["policy"]
    assert replay_payload["execution"]["exchange_latency_ms"] >= 0
