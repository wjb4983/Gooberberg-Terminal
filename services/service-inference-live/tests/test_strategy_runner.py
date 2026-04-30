from datetime import UTC, datetime
from uuid import uuid4

from gb_core.event_schemas import MarketDataEvent
from service_inference_live.strategy_runner import InMemoryRationaleStore, StrategyRunner


def _market_event(*, last: float) -> MarketDataEvent:
    now = datetime.now(UTC)
    return MarketDataEvent(
        event_id=uuid4(),
        trace_id=uuid4(),
        schema_version="v1",
        event_type="MarketDataEvent",
        event_time=now,
        ingest_time=now,
        process_time=now,
        producer="tests",
        strategy_version="strategy.v1",
        config_hash="abc123",
        symbol="AAPL",
        venue="XNAS",
        bid=100,
        ask=101,
        last=last,
        volume=900_000,
    )


def test_strategy_runner_emits_signal_and_auditable_decision() -> None:
    store = InMemoryRationaleStore()
    runner = StrategyRunner(
        producer="service-inference-live",
        strategy_version="momentum.v2",
        config_hash="cfg-v2",
        rationale_store=store,
    )

    signal, decision = runner.run(_market_event(last=101.5))

    assert signal.event_type == "SignalEvent"
    assert decision.event_type == "DecisionEvent"
    assert decision.go_no_go is True
    assert decision.confidence > 0
    assert decision.feature_snapshot_ref == f"signal:{signal.event_id}:features"

    metadata = store.by_decision_event_id(decision.event_id)
    assert metadata is not None
    assert metadata.rationale_kind == "rule"
    assert metadata.feature_snapshot == signal.features
    assert metadata.rationale_payload["signal_name"] == signal.signal_name


def test_strategy_runner_marks_hold_as_no_go() -> None:
    store = InMemoryRationaleStore()
    runner = StrategyRunner(
        producer="service-inference-live",
        strategy_version="momentum.v2",
        config_hash="cfg-v2",
        rationale_store=store,
    )

    _, decision = runner.run(_market_event(last=100.52))

    assert decision.decision == "hold"
    assert decision.go_no_go is False
    assert "strength_inside_no_trade_band" in decision.reasons
