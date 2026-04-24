import asyncio
import contextlib
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.ws.manager import ConnectionManager

router = APIRouter(tags=["ws"])
logger = logging.getLogger(__name__)
settings = get_settings()
manager = ConnectionManager(replay_window=settings.ws_replay_window)
VALID_TOPICS = {"jobs", "alerts", "logs", "portfolio", "risk", "strategy", "models", "backtests"}


async def _heartbeat(websocket: WebSocket, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await manager.send_json(websocket, {"type": "ping"})


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    connection_id = manager.connection_id(websocket)
    client = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(
        "websocket connected",
        extra={
            "event": "ws_connect",
            "connection_id": connection_id,
            "client": client,
        },
    )

    last_seq_raw = websocket.query_params.get("last_seq")
    last_seq: int | None = None
    if last_seq_raw is not None:
        if last_seq_raw.isdigit():
            last_seq = int(last_seq_raw)
        else:
            logger.info(
                "websocket replay rejected invalid cursor",
                extra={
                    "event": "ws_replay",
                    "connection_id": connection_id,
                    "client": client,
                    "last_seq": last_seq_raw,
                    "replay_status": "invalid",
                },
            )
            await manager.send_json(
                websocket,
                {
                    "type": "replay_cursor_invalid",
                    "detail": "last_seq must be a non-negative integer",
                },
            )

    heartbeat_task = asyncio.create_task(
        _heartbeat(websocket, settings.heartbeat_interval_seconds)
    )

    try:
        while True:
            message = await websocket.receive_text()
            normalized = message.strip().lower()
            if normalized in {"pong", "ping"}:
                await manager.send_json(websocket, {"type": "pong"})
                continue

            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                await manager.send_json(websocket, {"type": "error", "detail": "invalid json"})
                continue

            action = payload.get("action")
            requested_topics = payload.get("topics", [])
            topics = [topic for topic in requested_topics if topic in VALID_TOPICS]

            if action == "subscribe":
                subscriptions = manager.subscribe(websocket, topics)
                logger.info(
                    "websocket subscribed",
                    extra={
                        "event": "ws_subscribe",
                        "connection_id": connection_id,
                        "client": client,
                        "topics": subscriptions,
                    },
                )
                await manager.send_json(
                    websocket,
                    {"type": "subscribed", "topics": subscriptions},
                )

                if settings.ws_replay_enabled and last_seq is not None:
                    replay_result = await manager.replay_since(websocket, last_seq, subscriptions)
                    logger.info(
                        "websocket replay outcome",
                        extra={
                            "event": "ws_replay",
                            "connection_id": connection_id,
                            "client": client,
                            "last_seq": last_seq,
                            "replay_status": replay_result.status,
                            "replayed_count": replay_result.replayed_count,
                            "oldest_seq": replay_result.oldest_seq,
                            "latest_seq": replay_result.latest_seq,
                        },
                    )
                    if replay_result.status == "too_old":
                        await manager.send_json(
                            websocket,
                            {
                                "type": "replay_required",
                                "detail": "last_seq outside replay window",
                                "requested_last_seq": last_seq,
                                "oldest_available_seq": replay_result.oldest_seq,
                                "latest_available_seq": replay_result.latest_seq,
                            },
                        )
                    elif replay_result.status == "ok":
                        await manager.send_json(
                            websocket,
                            {
                                "type": "replay_complete",
                                "replayed_count": replay_result.replayed_count,
                                "latest_available_seq": replay_result.latest_seq,
                            },
                        )
                    else:
                        await manager.send_json(
                            websocket,
                            {"type": "replay_cursor_invalid", "detail": "invalid replay cursor"},
                        )
                    last_seq = None
                elif not settings.ws_replay_enabled and last_seq is not None:
                    logger.info(
                        "websocket replay disabled",
                        extra={
                            "event": "ws_replay",
                            "connection_id": connection_id,
                            "client": client,
                            "last_seq": last_seq,
                            "replay_status": "disabled",
                        },
                    )
                    await manager.send_json(
                        websocket,
                        {
                            "type": "replay_disabled",
                            "detail": "replay is disabled by server feature flag",
                        },
                    )
                    last_seq = None
            elif action == "unsubscribe":
                subscriptions = manager.unsubscribe(websocket, topics)
                logger.info(
                    "websocket unsubscribed",
                    extra={
                        "event": "ws_unsubscribe",
                        "connection_id": connection_id,
                        "client": client,
                        "topics": subscriptions,
                    },
                )
                await manager.send_json(
                    websocket,
                    {"type": "unsubscribed", "topics": subscriptions},
                )
            else:
                await manager.send_json(
                    websocket,
                    {"type": "error", "detail": "unsupported action"},
                )
    except WebSocketDisconnect:
        logger.info(
            "websocket disconnected",
            extra={
                "event": "ws_disconnect",
                "connection_id": connection_id,
                "client": client,
            },
        )
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        manager.disconnect(websocket)
