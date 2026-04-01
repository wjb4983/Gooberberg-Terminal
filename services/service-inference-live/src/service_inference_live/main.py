"""Live inference skeleton that emits strategy intents for downstream risk evaluation."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from gb_core.schemas import OrderSide, StrategyIntent

if TYPE_CHECKING:
    from redis.asyncio import Redis

STRATEGY_INTENT_CHANNEL = os.getenv("GB_STRATEGY_INTENT_CHANNEL", "strategy.intent")
PUBLISH_INTERVAL_SECONDS = float(os.getenv("GB_INFERENCE_INTENT_INTERVAL_SECONDS", "2"))
HEALTH_HOST = os.getenv("GB_INFERENCE_HEALTH_HOST", "0.0.0.0")
HEALTH_PORT = int(os.getenv("GB_INFERENCE_HEALTH_PORT", "8091"))

logger = logging.getLogger("service_inference_live")

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[misc, assignment]


@dataclass
class ServiceState:
    emitted_intents: int = 0
    last_trace_id: str | None = None


def _active_strategy_instance_ids() -> list[UUID]:
    raw = os.getenv("GB_ACTIVE_STRATEGY_INSTANCE_IDS", "")
    if not raw.strip():
        return [uuid4()]

    ids: list[UUID] = []
    for token in raw.split(","):
        cleaned = token.strip()
        if not cleaned:
            continue
        ids.append(UUID(cleaned))
    return ids


def _build_mock_intent(strategy_instance_id: UUID, seq: int) -> StrategyIntent:
    side = OrderSide.BUY if seq % 2 == 0 else OrderSide.SELL
    qty = 10 + (seq % 5)
    limit_price = 190 + (seq % 10)
    trace_id = uuid4()
    confidence = round(0.55 + ((seq % 40) / 100), 3)

    return StrategyIntent(
        strategy_instance_id=strategy_instance_id,
        strategy_key="momentum.v1",
        symbol="AAPL",
        side=side,
        quantity=float(qty),
        limit_price=float(limit_price),
        notes="mock inference intent; execution delegated to risk service",
        trace_id=trace_id,
        confidence=confidence,
        params={"seq": seq, "generator": "service-inference-live"},
    )


async def _publish_intents(client: "Redis", state: ServiceState) -> None:
    strategy_ids = _active_strategy_instance_ids()
    logger.info("starting intent loop strategy_instances=%s", len(strategy_ids))
    seq = 0

    while True:
        for strategy_instance_id in strategy_ids:
            intent = _build_mock_intent(strategy_instance_id, seq)
            payload_json = intent.model_dump_json()
            await client.publish(STRATEGY_INTENT_CHANNEL, payload_json)
            state.emitted_intents += 1
            state.last_trace_id = str(intent.trace_id)
            logger.info(
                "intent emitted channel=%s intent_id=%s strategy_instance_id=%s trace_id=%s confidence=%.3f",
                STRATEGY_INTENT_CHANNEL,
                intent.intent_id,
                strategy_instance_id,
                intent.trace_id,
                intent.confidence,
            )
            seq += 1
        await asyncio.sleep(PUBLISH_INTERVAL_SECONDS)


class _HealthHandler(BaseHTTPRequestHandler):
    state: ServiceState

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        payload = {
            "service": "service-inference-live",
            "status": "healthy",
            "emitted_intents": self.state.emitted_intents,
            "last_trace_id": self.state.last_trace_id,
            "publishes_to": STRATEGY_INTENT_CHANNEL,
            "execution_authority": "service-risk-exec",
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        logger.debug("health: " + fmt, *args)


def _start_health_server(state: ServiceState) -> ThreadingHTTPServer:
    _HealthHandler.state = state
    server = ThreadingHTTPServer((HEALTH_HOST, HEALTH_PORT), _HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    logger.info("health endpoint listening on http://%s:%s/health", HEALTH_HOST, HEALTH_PORT)
    return server


async def run() -> None:
    logging.basicConfig(level=os.getenv("GB_LOG_LEVEL", "INFO"))
    redis_dsn = os.getenv("GB_REDIS_DSN")
    state = ServiceState()
    health_server = _start_health_server(state)

    if not Redis or not redis_dsn:
        logger.warning("service-inference-live idle: redis unavailable")
        return

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    try:
        await client.ping()
        logger.info(
            "connected to redis and publishing strategy intents only; order placement is intentionally not implemented"
        )
        await _publish_intents(client, state)
    finally:
        health_server.shutdown()
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
