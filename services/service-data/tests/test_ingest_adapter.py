from __future__ import annotations

from datetime import UTC, datetime, timedelta

from service_data.market_data.ingest_adapter import FeedIngestAdapter


def _payload(**overrides: object) -> dict[str, object]:
    base = {
        "symbol": "AAPL",
        "venue": "XNAS",
        "event_time": datetime(2026, 4, 30, 12, 0, tzinfo=UTC),
        "sequence": 10,
        "bid": 189.1,
        "ask": 189.2,
        "last": 189.15,
        "volume": 100,
    }
    base.update(overrides)
    return base


def test_ingest_normalizes_into_market_data_event() -> None:
    adapter = FeedIngestAdapter(heartbeat_interval=timedelta(hours=1))
    result = adapter.ingest(_payload(), received_at=datetime(2026, 4, 30, 12, 0, 1, tzinfo=UTC))

    assert len(result.market_data) == 1
    assert result.market_data[0].event_type == "MarketDataEvent"
    assert result.market_data[0].symbol == "AAPL"


def test_duplicate_detection_routes_warning_alert() -> None:
    adapter = FeedIngestAdapter(heartbeat_interval=timedelta(hours=1))
    now = datetime(2026, 4, 30, 12, 0, 1, tzinfo=UTC)
    adapter.ingest(_payload(), received_at=now)
    dup = adapter.ingest(_payload(), received_at=now)

    assert len(dup.market_data) == 0
    assert any(a.category == "duplicate" and a.severity == "warning" for a in dup.alerts)


def test_sequence_regression_routes_critical_alert() -> None:
    adapter = FeedIngestAdapter(heartbeat_interval=timedelta(hours=1))
    now = datetime(2026, 4, 30, 12, 0, 1, tzinfo=UTC)
    adapter.ingest(_payload(sequence=12), received_at=now)
    out = adapter.ingest(_payload(sequence=11), received_at=now)

    assert any(a.category == "sequence" and a.severity == "critical" for a in out.alerts)


def test_stale_and_clock_skew_alerts() -> None:
    adapter = FeedIngestAdapter(
        stale_after=timedelta(seconds=2),
        max_clock_skew=timedelta(seconds=2),
        heartbeat_interval=timedelta(hours=1),
    )
    now = datetime(2026, 4, 30, 12, 0, 10, tzinfo=UTC)
    out = adapter.ingest(_payload(event_time=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)), received_at=now)

    categories = {a.category for a in out.alerts}
    assert "stale_data" in categories
    assert "clock_skew" in categories


def test_heartbeat_generation_emits_info_alert() -> None:
    adapter = FeedIngestAdapter(heartbeat_interval=timedelta(seconds=5))
    t0 = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)

    first = adapter.ingest(_payload(sequence=1), received_at=t0)
    second = adapter.ingest(_payload(sequence=2), received_at=t0 + timedelta(seconds=1))
    third = adapter.ingest(_payload(sequence=3), received_at=t0 + timedelta(seconds=6))

    assert any(a.category == "heartbeat" and a.severity == "info" for a in first.alerts)
    assert not any(a.category == "heartbeat" for a in second.alerts)
    assert any(a.category == "heartbeat" for a in third.alerts)
