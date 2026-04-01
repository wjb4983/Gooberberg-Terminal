import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.routers import ws as ws_router


@pytest.fixture(autouse=True)
def _reset_ws_manager_state() -> None:
    ws_router.manager._connections.clear()  # type: ignore[attr-defined]
    ws_router.manager._subscriptions.clear()  # type: ignore[attr-defined]
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
