import asyncio
from collections import deque
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


@dataclass(slots=True)
class ReplayResult:
    status: str
    replayed_count: int = 0
    oldest_seq: int | None = None
    latest_seq: int | None = None


class ConnectionManager:
    def __init__(self, replay_window: int = 512) -> None:
        self._connections: set[WebSocket] = set()
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._seq = 0
        self._lock = asyncio.Lock()
        self._replay_window = max(1, replay_window)
        self._event_buffer: deque[BroadcastEvent] = deque(maxlen=self._replay_window)
        self._connection_ids: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        self._subscriptions[websocket] = set()
        self._connection_ids[websocket] = str(uuid4())

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        self._subscriptions.pop(websocket, None)
        self._connection_ids.pop(websocket, None)

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
            self._event_buffer.append(event)

        sockets = [
            ws for ws in self._connections if topic in self._subscriptions.get(ws, set())
        ]
        if sockets:
            await self._send_many(sockets, event.to_json())
        return event

    async def replay_since(self, websocket: WebSocket, last_seq: int, topics: Iterable[str]) -> ReplayResult:
        if last_seq < 0:
            return ReplayResult(status="invalid")

        topic_filter = set(topics)
        if not self._event_buffer:
            return ReplayResult(status="ok", replayed_count=0)

        oldest_seq = self._event_buffer[0].seq
        latest_seq = self._event_buffer[-1].seq

        if last_seq < oldest_seq - 1:
            return ReplayResult(status="too_old", oldest_seq=oldest_seq, latest_seq=latest_seq)

        replayable = [
            event for event in self._event_buffer
            if event.seq > last_seq and event.topic in topic_filter
        ]
        for event in replayable:
            await websocket.send_json(event.to_json())

        return ReplayResult(
            status="ok",
            replayed_count=len(replayable),
            oldest_seq=oldest_seq,
            latest_seq=latest_seq,
        )

    def topic_subscriber_count(self, topic: str) -> int:
        return sum(1 for subs in self._subscriptions.values() if topic in subs)

    def all_connections(self) -> Iterable[WebSocket]:
        return self._connections

    def connection_id(self, websocket: WebSocket) -> str | None:
        return self._connection_ids.get(websocket)

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
