import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import WebSocket


@dataclass(slots=True)
class BroadcastEvent:
    event_id: str
    seq: int
    topic: str
    timestamp: str
    payload: dict
    version: str = "1.0"
    envelope_version: str = "1.0"
    contract_name: str = "gb.ws.event"
    contract_version: str = "1.0"

    def to_json(self) -> dict:
        return {
            "event_id": self.event_id,
            "seq": self.seq,
            "topic": self.topic,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "version": self.version,
            "envelope_version": self.envelope_version,
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
        }


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._seq = 0
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        self._subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        self._subscriptions.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, topics: Iterable[str]) -> list[str]:
        subscriptions = self._subscriptions.setdefault(websocket, set())
        subscriptions.update(topics)
        return sorted(subscriptions)

    def unsubscribe(self, websocket: WebSocket, topics: Iterable[str]) -> list[str]:
        subscriptions = self._subscriptions.setdefault(websocket, set())
        subscriptions.difference_update(topics)
        return sorted(subscriptions)

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def send_json(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_json(payload)

    async def broadcast_json(self, payload: dict) -> None:
        await self._send_many(self._connections, payload)

    async def publish_topic(self, topic: str, payload: dict, version: str = "1.0") -> BroadcastEvent:
        async with self._lock:
            self._seq += 1
            event = BroadcastEvent(
                event_id=str(uuid4()),
                seq=self._seq,
                topic=topic,
                timestamp=datetime.now(UTC).isoformat(),
                payload=payload,
                version=version,
            )

        sockets = [
            ws for ws in self._connections if topic in self._subscriptions.get(ws, set())
        ]
        if sockets:
            await self._send_many(sockets, event.to_json())
        return event

    def topic_subscriber_count(self, topic: str) -> int:
        return sum(1 for subs in self._subscriptions.values() if topic in subs)

    def all_connections(self) -> Iterable[WebSocket]:
        return self._connections

    async def _send_many(self, sockets: Iterable[WebSocket], payload: dict) -> None:
        socket_list = list(sockets)
        if not socket_list:
            return
        results = await asyncio.gather(
            *(ws.send_json(payload) for ws in socket_list),
            return_exceptions=True,
        )
        for socket, result in zip(socket_list, results, strict=False):
            if isinstance(result, Exception):
                self.disconnect(socket)
