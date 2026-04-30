"""Risk execution service skeleton that consumes strategy intent events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from random import Random


class OrderState(StrEnum):
    CREATED = "created"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class MarketEvent:
    symbol: str
    displayed_qty: float
    observed_spread: float | None = None


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    qty: float
    aggressive: bool
    participation: float


@dataclass(frozen=True)
class FillResult:
    fill_qty: float
    state: OrderState
    fee_amt: float
    spread_cost: float
    impact_cost: float
    delay_cost: float


class FeeModel:
    def fee_amount(self, order: OrderRequest, fill_qty: float) -> float:
        raise NotImplementedError


class SlippageModel:
    def slippage_bps(self, participation: float) -> float:
        raise NotImplementedError


class SpreadModel:
    def spread(self, event: MarketEvent) -> float:
        raise NotImplementedError


class LatencyModel:
    def latency_ms(self) -> float:
        raise NotImplementedError


class FillModel:
    def max_fill_qty(self, order: OrderRequest, event: MarketEvent) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class FixedBpsFeeModel(FeeModel):
    fixed_fee: float = 0.0
    maker_bps: float = 0.0
    taker_bps: float = 0.0

    def fee_amount(self, order: OrderRequest, fill_qty: float) -> float:
        bps = self.taker_bps if order.aggressive else self.maker_bps
        return self.fixed_fee + fill_qty * (bps / 10_000)


@dataclass(frozen=True)
class PowerLawSlippageModel(SlippageModel):
    a: float = 0.0
    b: float = 0.0
    gamma: float = 1.0

    def slippage_bps(self, participation: float) -> float:
        bounded = min(max(participation, 0.0), 1.0)
        return self.a + self.b * (bounded**self.gamma)


@dataclass(frozen=True)
class ObservedOrFallbackSpreadModel(SpreadModel):
    fallback_by_symbol: dict[str, float]
    default_spread: float = 0.01

    def spread(self, event: MarketEvent) -> float:
        if event.observed_spread is not None:
            return event.observed_spread
        return self.fallback_by_symbol.get(event.symbol, self.default_spread)


@dataclass
class BasePlusJitterLatencyModel(LatencyModel):
    base_ms: float
    jitter_ms: float
    random: Random | None = None

    def latency_ms(self) -> float:
        rng = self.random or Random(0)
        return self.base_ms + rng.uniform(0.0, self.jitter_ms)


@dataclass(frozen=True)
class ParticipationCapFillModel(FillModel):
    participation_cap: float

    def max_fill_qty(self, order: OrderRequest, event: MarketEvent) -> float:
        cap = max(self.participation_cap, 0.0)
        return min(order.qty, event.displayed_qty * cap)


@dataclass
class ExecutionEngine:
    fee_model: FeeModel
    slippage_model: SlippageModel
    spread_model: SpreadModel
    latency_model: LatencyModel
    fill_model: FillModel

    def process_fill(self, order: OrderRequest, event: MarketEvent) -> FillResult:
        max_fill_qty = self.fill_model.max_fill_qty(order, event)
        fill_qty = max(0.0, min(order.qty, max_fill_qty))

        if fill_qty <= 0:
            return FillResult(fill_qty=0.0, state=OrderState.ACKNOWLEDGED, fee_amt=0.0, spread_cost=0.0, impact_cost=0.0, delay_cost=0.0)

        fill_state = OrderState.FILLED if fill_qty >= order.qty else OrderState.PARTIALLY_FILLED
        spread = self.spread_model.spread(event)
        impact_bps = self.slippage_model.slippage_bps(order.participation)
        delay_ms = self.latency_model.latency_ms()

        return FillResult(
            fill_qty=fill_qty,
            state=fill_state,
            fee_amt=self.fee_model.fee_amount(order, fill_qty),
            spread_cost=fill_qty * spread,
            impact_cost=fill_qty * (impact_bps / 10_000),
            delay_cost=fill_qty * (delay_ms / 1000),
        )

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TYPE_CHECKING

from gb_core.risk import RiskExecutionAuthority
from gb_core.schemas import ExecutionDecision, StrategyIntent

if TYPE_CHECKING:
    from redis.asyncio import Redis

STRATEGY_INTENT_CHANNEL = os.getenv("GB_STRATEGY_INTENT_CHANNEL", "strategy.intent")
RISK_DECISION_CHANNEL = os.getenv("GB_RISK_DECISION_CHANNEL", "risk.decision")
HEALTH_HOST = os.getenv("GB_RISK_HEALTH_HOST", "0.0.0.0")
HEALTH_PORT = int(os.getenv("GB_RISK_HEALTH_PORT", "8092"))

logger = logging.getLogger("service_risk_exec")
authority = RiskExecutionAuthority()

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover
    Redis = None  # type: ignore[misc, assignment]


@dataclass
class ServiceState:
    processed_intents: int = 0
    approved_decisions: int = 0


def consume_strategy_intent(intent: StrategyIntent) -> ExecutionDecision:
    """Consume a strategy intent event and emit an execution decision."""
    return authority.consume_intent(intent)


async def _consume_intent_payload(client: "Redis", payload: str, state: ServiceState) -> None:
    intent = StrategyIntent.model_validate_json(payload)
    decision = consume_strategy_intent(intent)
    state.processed_intents += 1
    if decision.approved:
        state.approved_decisions += 1

    logger.info(
        "risk decision emitted intent_id=%s approved=%s reason=%s trace_id=%s confidence=%s",
        intent.intent_id,
        decision.approved,
        decision.reason_code,
        intent.trace_id,
        intent.confidence,
    )
    decision_payload = {
        "intent": intent.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
        "execution_status": OrderState.CREATED,
        "order_lifecycle": [
            OrderState.CREATED,
            OrderState.SENT,
            OrderState.ACKNOWLEDGED,
            OrderState.PARTIALLY_FILLED,
            OrderState.FILLED,
        ],
        "authority_boundary": "risk-exec produces decisions only; order adapters are external",
    }
    await client.publish(RISK_DECISION_CHANNEL, json.dumps(decision_payload, default=str))


async def _run_consumer(client: "Redis", state: ServiceState) -> None:
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    await pubsub.subscribe(STRATEGY_INTENT_CHANNEL)
    logger.info("subscribed to channel=%s", STRATEGY_INTENT_CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(timeout=1.0)
            if not message:
                await asyncio.sleep(0.05)
                continue
            data = message.get("data")
            if not isinstance(data, str):
                logger.warning("received non-string message on %s", STRATEGY_INTENT_CHANNEL)
                continue
            await _consume_intent_payload(client, data, state)
    finally:
        await pubsub.unsubscribe(STRATEGY_INTENT_CHANNEL)
        await pubsub.aclose()


class _HealthHandler(BaseHTTPRequestHandler):
    state: ServiceState

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        payload = {
            "service": "service-risk-exec",
            "status": "healthy",
            "consumes_from": STRATEGY_INTENT_CHANNEL,
            "processed_intents": self.state.processed_intents,
            "approved_decisions": self.state.approved_decisions,
            "order_placement": "not implemented in this service",
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
        logger.warning("service-risk-exec idle: redis unavailable")
        return

    client = Redis.from_url(redis_dsn, encoding="utf-8", decode_responses=True)
    try:
        await client.ping()
        logger.info("connected to redis; awaiting strategy intents")
        await _run_consumer(client, state)
    finally:
        health_server.shutdown()
        await client.aclose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
