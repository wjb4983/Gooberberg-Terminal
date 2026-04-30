from datetime import datetime, timedelta, UTC

from service_risk_exec.analytics import ExecutionAnalyticsEvent, ExecutionAnalyticsStore


def test_incremental_analytics_and_reconcile_consistency() -> None:
    store = ExecutionAnalyticsStore()
    t0 = datetime.now(UTC)
    events = [
        ExecutionAnalyticsEvent(
            event_id="e1",
            ts=t0,
            symbol="AAPL",
            strategy="mean-revert",
            side="buy",
            qty=10,
            price=100,
            mark_price=101,
            expected_price=100.5,
            predicted_edge=0.2,
            realized_edge=0.5,
            confidence=0.7,
            fees=1.0,
            slippage=0.5,
            latency_queue_ms=1,
            latency_risk_ms=2,
            latency_route_ms=3,
            latency_venue_ms=4,
        ),
        ExecutionAnalyticsEvent(
            event_id="e2",
            ts=t0 + timedelta(seconds=1),
            symbol="AAPL",
            strategy="mean-revert",
            side="sell",
            qty=5,
            price=102,
            mark_price=101.5,
            expected_price=101.8,
            predicted_edge=0.1,
            realized_edge=-0.3,
            confidence=0.4,
            fees=0.5,
            slippage=0.2,
            latency_queue_ms=2,
            latency_risk_ms=1,
            latency_route_ms=2,
            latency_venue_ms=5,
        ),
    ]
    for event in events:
        store.update_incremental(event)
    before = store.metrics_snapshot()
    store.reconcile_full()
    after = store.metrics_snapshot()
    assert before == after
    assert "pnl_attribution" in after
    assert "drawdown" in after
    assert "exposure" in after
    assert "turnover" in after
    assert "latency_stage_breakdown_ms" in after
    assert "decision_quality" in after
