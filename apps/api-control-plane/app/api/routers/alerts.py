from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.api.routers.ws import manager as ws_manager
from app.schemas import (
    AlertAcknowledgeResponse,
    AlertEvent,
    AlertLifecycleEvent,
    AlertLifecycleType,
    AlertSeverity,
    AlertStatus,
    LogEvent,
    LogLevel,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])

_alert_store: dict[UUID, AlertEvent] = {}
_alert_last_emitted: dict[str, datetime] = {}
_alert_lifecycle_store: dict[UUID, list[AlertLifecycleEvent]] = {}
_escalation_levels: dict[UUID, int] = {}

_SUPPRESSION_WINDOWS_SECONDS = {
    AlertSeverity.INFO: 60,
    AlertSeverity.WARNING: 300,
    AlertSeverity.CRITICAL: 900,
}
_ESCALATION_LADDER_MINUTES = [5, 15, 30]


def _seed_alerts() -> None:
    if _alert_store:
        return

    now = datetime.now(UTC)
    for alert in [
        AlertEvent(
            service="service-risk-exec",
            level=AlertSeverity.CRITICAL,
            trace_id="trace-risk-drawdown",
            message="Risk limit breached for strategy alpha.",
            category="risk",
            timestamp=now,
        ),
        AlertEvent(
            service="service-data",
            level=AlertSeverity.WARNING,
            trace_id="trace-data-lag",
            message="Market data stream lag exceeds threshold.",
            category="data",
            timestamp=now,
        ),
    ]:
        _alert_store[alert.id] = alert
        _record_lifecycle(alert.id, AlertLifecycleType.TRIGGERED, {"seeded": True})
        _escalation_levels[alert.id] = 0


def _record_lifecycle(alert_id: UUID, event_type: AlertLifecycleType, details: dict[str, str | int | bool]) -> None:
    _alert_lifecycle_store.setdefault(alert_id, []).append(
        AlertLifecycleEvent(alert_id=alert_id, event_type=event_type, details=details)
    )


def _suppression_key(alert: AlertEvent) -> str:
    return f"{alert.service}:{alert.category}:{alert.message}:{alert.level.value}"


def _should_suppress(alert: AlertEvent) -> bool:
    last_emitted = _alert_last_emitted.get(_suppression_key(alert))
    if last_emitted is None:
        return False
    return (datetime.now(UTC) - last_emitted).total_seconds() < _SUPPRESSION_WINDOWS_SECONDS[alert.level]


async def _route_alert(alert: AlertEvent) -> None:
    settings = get_settings()
    channels = ["desktop", "webhook"]
    if settings.api_auth_token:
        channels.append("email")
    if settings.api_auth_tokens:
        channels.append("slack")
    _record_lifecycle(alert.id, AlertLifecycleType.TRIGGERED, {"channels": ",".join(channels)})
    await ws_manager.publish_topic(
        topic="logs",
        payload=LogEvent(
            service="api-control-plane",
            level=LogLevel.INFO,
            trace_id=alert.trace_id,
            message=f"Alert {alert.id} routed",
            category="alerts",
            fields={"alert_id": str(alert.id), "channels": channels},
        ).model_dump(mode="json"),
    )


async def _evaluate_escalations() -> None:
    now = datetime.now(UTC)
    for alert in _alert_store.values():
        if alert.level != AlertSeverity.CRITICAL or alert.status in {AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED}:
            continue
        age_minutes = (now - alert.timestamp).total_seconds() / 60
        current_level = _escalation_levels.get(alert.id, 0)
        if current_level < len(_ESCALATION_LADDER_MINUTES) and age_minutes >= _ESCALATION_LADDER_MINUTES[current_level]:
            _escalation_levels[alert.id] = current_level + 1
            alert.status = AlertStatus.ESCALATED
            _record_lifecycle(
                alert.id,
                AlertLifecycleType.ESCALATED,
                {"ladder_level": current_level + 1, "threshold_minutes": _ESCALATION_LADDER_MINUTES[current_level]},
            )


@router.get("", response_model=list[AlertEvent])
async def list_alerts() -> list[AlertEvent]:
    _seed_alerts()
    await _evaluate_escalations()
    return sorted(_alert_store.values(), key=lambda item: item.timestamp, reverse=True)


@router.post("/{alert_id}/ack", response_model=AlertAcknowledgeResponse)
async def acknowledge_alert(alert_id: UUID) -> AlertAcknowledgeResponse:
    _seed_alerts()
    alert = _alert_store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert not found")

    if alert.status == AlertStatus.ACKNOWLEDGED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="alert already acknowledged")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(UTC)
    _record_lifecycle(alert.id, AlertLifecycleType.ACKNOWLEDGED, {"source": "api"})

    await ws_manager.publish_topic(topic="alerts", payload=alert.model_dump(mode="json"))
    await ws_manager.publish_topic(
        topic="logs",
        payload=LogEvent(
            timestamp=alert.acknowledged_at,
            service="api-control-plane",
            level=LogLevel.INFO,
            trace_id=alert.trace_id,
            message=f"Alert {alert.id} acknowledged",
            category="alerts",
            fields={"alert_id": str(alert.id), "service": alert.service, "severity": alert.level.value},
        ).model_dump(mode="json"),
    )

    return AlertAcknowledgeResponse(alert=alert, detail="alert acknowledged")


@router.post("/emit", response_model=AlertEvent, status_code=status.HTTP_201_CREATED)
async def emit_alert(alert: AlertEvent) -> AlertEvent:
    _seed_alerts()
    if _should_suppress(alert):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="alert suppressed by deduplication window")
    _alert_store[alert.id] = alert
    _alert_last_emitted[_suppression_key(alert)] = datetime.now(UTC)
    _escalation_levels[alert.id] = 0
    _record_lifecycle(alert.id, AlertLifecycleType.TRIGGERED, {"source": "api"})
    await _route_alert(alert)
    await ws_manager.publish_topic(topic="alerts", payload=alert.model_dump(mode="json"))
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertEvent)
async def resolve_alert(alert_id: UUID) -> AlertEvent:
    _seed_alerts()
    alert = _alert_store.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert not found")
    alert.status = AlertStatus.RESOLVED
    _record_lifecycle(alert.id, AlertLifecycleType.RESOLVED, {"source": "api"})
    await ws_manager.publish_topic(topic="alerts", payload=alert.model_dump(mode="json"))
    return alert


@router.get("/{alert_id}/lifecycle", response_model=list[AlertLifecycleEvent])
async def alert_lifecycle(alert_id: UUID) -> list[AlertLifecycleEvent]:
    _seed_alerts()
    if alert_id not in _alert_store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert not found")
    return _alert_lifecycle_store.get(alert_id, [])
