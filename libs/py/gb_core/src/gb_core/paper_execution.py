from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import ceil
from uuid import UUID, uuid4

from gb_core.event_schemas import FillEvent, OrderEvent, OrderIntentEvent


@dataclass(slots=True)
class PaperExecutionConfig:
    base_latency_ms: float = 5.0
    jitter_latency_ms: float = 0.0
    slippage_bps: float = 2.0
    queue_ahead_qty: float = 0.0
    max_fill_slices: int = 4
    reject_if_missing_limit: bool = False


@dataclass(slots=True)
class PaperExecutionResult:
    order_events: list[OrderEvent]
    fill_events: list[FillEvent]


@dataclass(slots=True)
class _OrderProgress:
    order_id: UUID
    emitted_fill_keys: set[str] = field(default_factory=set)
    emitted_qty: float = 0.0


class PaperExecutionEngine:
    """Deterministic paper execution for order intents with idempotent emissions."""

    def __init__(self, config: PaperExecutionConfig | None = None) -> None:
        self.config = config or PaperExecutionConfig()
        self._intent_results: dict[str, PaperExecutionResult] = {}
        self._progress: dict[str, _OrderProgress] = {}

    def process_intent(self, intent: OrderIntentEvent, *, idempotency_key: str) -> PaperExecutionResult:
        if idempotency_key in self._intent_results:
            return self._intent_results[idempotency_key]

        now = datetime.now(UTC)
        order_id = uuid4()
        order_events: list[OrderEvent] = []
        fill_events: list[FillEvent] = []

        order_events.append(self._order_event(intent, order_id, "submitted", now))

        if self.config.reject_if_missing_limit and intent.limit_price is None:
            order_events.append(self._order_event(intent, order_id, "rejected", now + timedelta(milliseconds=1)))
            result = PaperExecutionResult(order_events=order_events, fill_events=[])
            self._intent_results[idempotency_key] = result
            return result

        ack_at = now + timedelta(milliseconds=self._latency_ms(idempotency_key))
        order_events.append(self._order_event(intent, order_id, "ack", ack_at))

        progress = _OrderProgress(order_id=order_id)
        self._progress[idempotency_key] = progress

        total_qty = float(intent.quantity)
        if total_qty <= 0:
            order_events.append(self._order_event(intent, order_id, "canceled", ack_at + timedelta(milliseconds=1)))
            result = PaperExecutionResult(order_events=order_events, fill_events=[])
            self._intent_results[idempotency_key] = result
            return result

        available_qty = max(total_qty - self.config.queue_ahead_qty, 0.0)
        if available_qty <= 0:
            order_events.append(self._order_event(intent, order_id, "canceled", ack_at + timedelta(milliseconds=1)))
            result = PaperExecutionResult(order_events=order_events, fill_events=[])
            self._intent_results[idempotency_key] = result
            return result

        slices = max(1, self.config.max_fill_slices)
        slice_qty = min(total_qty / slices, available_qty)
        remaining = total_qty

        for idx in range(slices):
            fill_qty = min(slice_qty, remaining)
            if fill_qty <= 0:
                break
            fill_key = f"{idempotency_key}:fill:{idx}"
            if fill_key in progress.emitted_fill_keys:
                continue
            progress.emitted_fill_keys.add(fill_key)
            remaining -= fill_qty
            progress.emitted_qty += fill_qty
            fill_events.append(self._fill_event(intent, progress.order_id, fill_qty, ack_at + timedelta(milliseconds=idx + 1), fill_key))

        if progress.emitted_qty < total_qty:
            order_events.append(self._order_event(intent, order_id, "canceled", ack_at + timedelta(milliseconds=slices + 1)))

        result = PaperExecutionResult(order_events=order_events, fill_events=fill_events)
        self._intent_results[idempotency_key] = result
        return result

    def _latency_ms(self, key: str) -> float:
        if self.config.jitter_latency_ms <= 0:
            return self.config.base_latency_ms
        digest = sha256(key.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:2], "big") / 65535
        return self.config.base_latency_ms + bucket * self.config.jitter_latency_ms

    def _price_with_slippage(self, intent: OrderIntentEvent) -> float:
        ref = float(intent.limit_price or 100.0)
        slip = ref * (self.config.slippage_bps / 10_000)
        return ref + slip if intent.side == "buy" else max(ref - slip, 0.01)

    def _order_event(self, intent: OrderIntentEvent, order_id: UUID, status: str, at: datetime) -> OrderEvent:
        return OrderEvent(
            event_id=uuid4(),
            trace_id=intent.trace_id,
            schema_version=intent.schema_version,
            event_type="OrderEvent",
            event_time=at,
            ingest_time=at,
            process_time=at,
            producer="paper-execution",
            strategy_version=intent.strategy_version,
            config_hash=intent.config_hash,
            order_id=order_id,
            intent_id=intent.intent_id,
            status=status,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
        )

    def _fill_event(self, intent: OrderIntentEvent, order_id: UUID, qty: float, at: datetime, fill_key: str) -> FillEvent:
        status = "full" if qty >= intent.quantity else "partial"
        return FillEvent(
            event_id=uuid4(),
            trace_id=intent.trace_id,
            schema_version=intent.schema_version,
            event_type="FillEvent",
            event_time=at,
            ingest_time=at,
            process_time=at,
            producer="paper-execution",
            strategy_version=intent.strategy_version,
            config_hash=intent.config_hash,
            order_id=order_id,
            fill_id=uuid5_from_key(fill_key),
            symbol=intent.symbol,
            side=intent.side,
            quantity=qty,
            price=self._price_with_slippage(intent),
            fill_status=status,
        )


def uuid5_from_key(key: str) -> UUID:
    digest = sha256(key.encode("utf-8")).digest()
    raw = bytearray(digest[:16])
    raw[6] = (raw[6] & 0x0F) | 0x50
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))
