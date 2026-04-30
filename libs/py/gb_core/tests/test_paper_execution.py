from datetime import UTC, datetime
from uuid import uuid4

from gb_core.event_schemas import OrderIntentEvent
from gb_core.paper_execution import PaperExecutionConfig, PaperExecutionEngine


def _intent(*, qty: float = 10, limit: float | None = 100.0) -> OrderIntentEvent:
    now = datetime(2026, 4, 30, tzinfo=UTC)
    return OrderIntentEvent(
        event_id=uuid4(),
        trace_id=uuid4(),
        schema_version="1.0.0",
        event_type="OrderIntentEvent",
        event_time=now,
        ingest_time=now,
        process_time=now,
        producer="strategy",
        strategy_version="v1",
        config_hash="cfg",
        intent_id=uuid4(),
        symbol="AAPL",
        side="buy",
        quantity=qty,
        limit_price=limit,
    )


def test_process_intent_emits_order_and_fill_events() -> None:
    engine = PaperExecutionEngine(PaperExecutionConfig(base_latency_ms=1.0, slippage_bps=5.0, queue_ahead_qty=0.0, max_fill_slices=2))
    result = engine.process_intent(_intent(qty=10), idempotency_key="intent-1")

    assert [event.status for event in result.order_events] == ["submitted", "ack"]
    assert len(result.fill_events) == 2
    assert sum(fill.quantity for fill in result.fill_events) == 10
    assert all(fill.fill_status in {"partial", "full"} for fill in result.fill_events)


def test_process_intent_idempotent_and_no_duplicate_fills() -> None:
    engine = PaperExecutionEngine(PaperExecutionConfig(max_fill_slices=3))
    intent = _intent(qty=6)

    first = engine.process_intent(intent, idempotency_key="same-key")
    second = engine.process_intent(intent, idempotency_key="same-key")

    assert [f.fill_id for f in first.fill_events] == [f.fill_id for f in second.fill_events]
    assert len({f.fill_id for f in second.fill_events}) == len(second.fill_events)


def test_queue_can_cancel_unfilled_orders() -> None:
    engine = PaperExecutionEngine(PaperExecutionConfig(queue_ahead_qty=50.0))
    result = engine.process_intent(_intent(qty=10), idempotency_key="queued-out")

    assert [event.status for event in result.order_events] == ["submitted", "ack", "canceled"]
    assert result.fill_events == []


def test_reject_if_missing_limit_price() -> None:
    engine = PaperExecutionEngine(PaperExecutionConfig(reject_if_missing_limit=True))
    result = engine.process_intent(_intent(qty=10, limit=None), idempotency_key="reject-no-limit")

    assert [event.status for event in result.order_events] == ["submitted", "rejected"]
    assert result.fill_events == []
