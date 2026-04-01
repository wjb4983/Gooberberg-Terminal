import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.ws.manager import ConnectionManager

router = APIRouter(tags=["ws"])
logger = logging.getLogger(__name__)
manager = ConnectionManager()


async def _heartbeat(websocket: WebSocket, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await manager.send_json(websocket, {"type": "ping"})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    settings = get_settings()
    await manager.connect(websocket)
    logger.info("websocket connected; active=%s", manager.active_count)

    heartbeat_task = asyncio.create_task(
        _heartbeat(websocket, settings.heartbeat_interval_seconds)
    )

    try:
        while True:
            message = await websocket.receive_text()
            normalized = message.strip().lower()
            if normalized in {"pong", "ping"}:
                await manager.send_json(websocket, {"type": "pong"})
            else:
                await manager.send_json(
                    websocket,
                    {"type": "echo", "message": message},
                )
    except WebSocketDisconnect:
        logger.info("websocket disconnected")
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        manager.disconnect(websocket)
