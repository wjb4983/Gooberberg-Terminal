from datetime import UTC, datetime
from uuid import UUID

from app.schemas.events import AlertEvent, AlertSeverity, AlertStatus, LogEvent, LogLevel


def test_alert_event_schema_serialization_round_trip() -> None:
    event = AlertEvent(
        service="api-control-plane",
        level=AlertSeverity.CRITICAL,
        trace_id="trace-123",
        message="risk limit breached",
        category="risk",
        status=AlertStatus.ACTIVE,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )

    payload = event.model_dump(mode="json")
    restored = AlertEvent.model_validate(payload)

    assert restored.id == event.id
    assert restored.timestamp == event.timestamp
    assert restored.level == AlertSeverity.CRITICAL
    assert restored.status == AlertStatus.ACTIVE
    assert restored.category == "risk"


def test_log_event_schema_serialization_round_trip() -> None:
    event = LogEvent(
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        service="api-control-plane",
        level=LogLevel.INFO,
        trace_id="trace-456",
        message="job accepted",
        category="jobs",
        fields={"job_id": "11111111-1111-1111-1111-111111111111", "status": "queued"},
    )

    as_json = event.model_dump_json()
    restored = LogEvent.model_validate_json(as_json)

    assert restored.timestamp == event.timestamp
    assert restored.service == "api-control-plane"
    assert restored.level == LogLevel.INFO
    assert restored.trace_id == "trace-456"
    assert UUID(restored.fields["job_id"])  # validates string format remains a UUID
