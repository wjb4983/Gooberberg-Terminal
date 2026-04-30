from datetime import UTC, datetime, timedelta

from gb_core.event_log import EventLogPolicy, EventLogWriter, EventQuery


def _payload(*, event_type: str, symbol: str, event_time: datetime, trace_id: str = "t-1", decision_id: str = "d-1", order_id: str = "o-1") -> dict[str, object]:
    return {
        "event_type": event_type,
        "symbol": symbol,
        "event_time": event_time.isoformat(),
        "trace_id": trace_id,
        "decision_id": decision_id,
        "order_id": order_id,
    }


def test_idempotent_append_and_monotonic_offsets() -> None:
    writer = EventLogWriter()
    first = writer.append(idempotency_key="k-1", payload=_payload(event_type="FillEvent", symbol="AAPL", event_time=datetime(2026, 1, 1, tzinfo=UTC)))
    second = writer.append(idempotency_key="k-1", payload=_payload(event_type="FillEvent", symbol="AAPL", event_time=datetime(2026, 1, 1, tzinfo=UTC)))
    third = writer.append(idempotency_key="k-2", payload=_payload(event_type="OrderEvent", symbol="MSFT", event_time=datetime(2026, 1, 2, tzinfo=UTC)))

    assert first.offset == 0
    assert second.offset == 0
    assert third.offset == 1


def test_query_filters() -> None:
    writer = EventLogWriter()
    writer.append(idempotency_key="a", payload=_payload(event_type="FillEvent", symbol="AAPL", event_time=datetime(2026, 1, 1, tzinfo=UTC), trace_id="t-1", decision_id="d-1", order_id="o-1"))
    writer.append(idempotency_key="b", payload=_payload(event_type="OrderEvent", symbol="AAPL", event_time=datetime(2026, 1, 2, tzinfo=UTC), trace_id="t-2", decision_id="d-2", order_id="o-2"))
    writer.append(idempotency_key="c", payload=_payload(event_type="FillEvent", symbol="MSFT", event_time=datetime(2026, 1, 3, tzinfo=UTC), trace_id="t-3", decision_id="d-3", order_id="o-3"))

    assert len(writer.query(EventQuery(event_type="FillEvent"))) == 2
    assert len(writer.query(EventQuery(symbol="AAPL"))) == 2
    assert len(writer.query(EventQuery(start_time=datetime(2026, 1, 2, tzinfo=UTC), end_time=datetime(2026, 1, 3, tzinfo=UTC)))) == 2
    assert len(writer.query(EventQuery(trace_id="t-2"))) == 1
    assert len(writer.query(EventQuery(decision_id="d-3"))) == 1
    assert len(writer.query(EventQuery(order_id="o-1"))) == 1


def test_retention_archive_and_integrity_segments() -> None:
    writer = EventLogWriter(policy=EventLogPolicy(retention_period=timedelta(days=2), archive_after=timedelta(days=1)), segment_size=2)
    now = datetime(2026, 1, 5, tzinfo=UTC)
    writer.append(idempotency_key="1", payload=_payload(event_type="FillEvent", symbol="AAPL", event_time=now - timedelta(days=3)))
    writer.append(idempotency_key="2", payload=_payload(event_type="OrderEvent", symbol="AAPL", event_time=now - timedelta(days=1, hours=1)))
    writer.append(idempotency_key="3", payload=_payload(event_type="AlertEvent", symbol="AAPL", event_time=now))

    archived, purged = writer.apply_retention_and_archive(now=now)
    assert archived == 2
    assert purged == 1
    assert len(writer.archived_records) == 2

    segments = writer.integrity_segments()
    assert len(segments) == 1
    assert segments[0].event_count == 2
    assert len(segments[0].checksum) == 64
