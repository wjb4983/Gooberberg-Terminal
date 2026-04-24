import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.routers import ws as ws_router
from app.ws.manager import BroadcastEvent


@pytest.fixture(autouse=True)
def _reset_ws_manager_state() -> None:
    ws_router.manager._connections.clear()  # type: ignore[attr-defined]
    ws_router.manager._subscriptions.clear()  # type: ignore[attr-defined]
    ws_router.manager._connection_ids.clear()  # type: ignore[attr-defined]
    ws_router.manager._event_buffer.clear()  # type: ignore[attr-defined]
    ws_router.manager._seq = 0  # type: ignore[attr-defined]


def test_websocket_subscribe_acknowledges_valid_topics() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/ws") as websocket:
        websocket.send_json(
            {
                "action": "subscribe",
                "topics": ["jobs", "not-a-valid-topic"],
            }
        )
        response = websocket.receive_json()

    assert response == {"type": "subscribed", "topics": ["jobs"]}


def test_websocket_replay_cursor_invalid_event() -> None:
    client = TestClient(create_app())

    with client.websocket_connect("/ws?last_seq=nope") as websocket:
        response = websocket.receive_json()

    assert response == {
        "type": "replay_cursor_invalid",
        "detail": "last_seq must be a non-negative integer",
    }


def test_websocket_replays_from_last_seq_and_reports_complete() -> None:
    client = TestClient(create_app())
    ws_router.manager._seq = 3  # type: ignore[attr-defined]
    ws_router.manager._event_buffer.extend(  # type: ignore[attr-defined]
        [
            BroadcastEvent(
                event_id="e-2",
                seq=2,
                topic="jobs",
                timestamp=datetime.now(UTC).isoformat(),
                payload={"job_id": "j-2"},
            ),
            BroadcastEvent(
                event_id="e-3",
                seq=3,
                topic="jobs",
                timestamp=datetime.now(UTC).isoformat(),
                payload={"job_id": "j-3"},
            ),
        ]
    )

    with client.websocket_connect("/ws?last_seq=1") as websocket:
        websocket.send_json({"action": "subscribe", "topics": ["jobs"]})
        assert websocket.receive_json() == {"type": "subscribed", "topics": ["jobs"]}
        replayed = websocket.receive_json()
        assert replayed["seq"] == 2
        replayed = websocket.receive_json()
        assert replayed["seq"] == 3
        complete = websocket.receive_json()

    assert complete["type"] == "replay_complete"
    assert complete["replayed_count"] == 2
    assert complete["latest_available_seq"] == 3


def test_websocket_replay_reports_too_old_cursor() -> None:
    client = TestClient(create_app())
    ws_router.manager._seq = 7  # type: ignore[attr-defined]
    ws_router.manager._event_buffer.extend(  # type: ignore[attr-defined]
        [
            BroadcastEvent(
                event_id="e-5",
                seq=5,
                topic="jobs",
                timestamp=datetime.now(UTC).isoformat(),
                payload={"job_id": "j-5"},
            ),
            BroadcastEvent(
                event_id="e-6",
                seq=6,
                topic="jobs",
                timestamp=datetime.now(UTC).isoformat(),
                payload={"job_id": "j-6"},
            ),
        ]
    )

    with client.websocket_connect("/ws?last_seq=1") as websocket:
        websocket.send_json({"action": "subscribe", "topics": ["jobs"]})
        assert websocket.receive_json() == {"type": "subscribed", "topics": ["jobs"]}
        replay_required = websocket.receive_json()

    assert replay_required["type"] == "replay_required"
    assert replay_required["requested_last_seq"] == 1
    assert replay_required["oldest_available_seq"] == 5
    assert replay_required["latest_available_seq"] == 6


def test_websocket_replay_can_be_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ws_router.settings, "ws_replay_enabled", False)
    client = TestClient(create_app())
    ws_router.manager._seq = 2  # type: ignore[attr-defined]

    with client.websocket_connect("/ws?last_seq=1") as websocket:
        websocket.send_json({"action": "subscribe", "topics": ["jobs"]})
        assert websocket.receive_json() == {"type": "subscribed", "topics": ["jobs"]}
        replay_disabled = websocket.receive_json()

    assert replay_disabled == {
        "type": "replay_disabled",
        "detail": "replay is disabled by server feature flag",
    }


@pytest.mark.asyncio
async def test_heartbeat_sends_ping_without_timing_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_payloads: list[dict] = []

    class StubWebSocket:
        async def send_json(self, payload: dict) -> None:
            sent_payloads.append(payload)

    async def immediate_sleep(_: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(ws_router.asyncio, "sleep", immediate_sleep)

    with pytest.raises(asyncio.CancelledError):
        await ws_router._heartbeat(StubWebSocket(), interval_seconds=60.0)  # type: ignore[arg-type]

    assert sent_payloads == []


@pytest.mark.asyncio
async def test_heartbeat_emits_ping_when_sleep_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_payloads: list[dict] = []

    class StubWebSocket:
        async def send_json(self, payload: dict) -> None:
            sent_payloads.append(payload)
            raise asyncio.CancelledError

    async def no_wait(_: float) -> None:
        return None

    monkeypatch.setattr(ws_router.asyncio, "sleep", no_wait)

    with pytest.raises(asyncio.CancelledError):
        await ws_router._heartbeat(StubWebSocket(), interval_seconds=60.0)  # type: ignore[arg-type]

    assert sent_payloads == [{"type": "ping"}]
