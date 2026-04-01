import asyncio
from collections.abc import Iterable

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def send_json(self, websocket: WebSocket, payload: dict) -> None:
        await websocket.send_json(payload)

    async def broadcast_json(self, payload: dict) -> None:
        await asyncio.gather(*(ws.send_json(payload) for ws in self._connections))

    def all_connections(self) -> Iterable[WebSocket]:
        return self._connections
