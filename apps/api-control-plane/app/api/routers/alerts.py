from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.routers.ws import manager as ws_manager
from app.schemas import AlertAcknowledgeResponse, AlertEvent, AlertSeverity, AlertStatus, LogEvent, LogLevel

router = APIRouter(prefix="/alerts", tags=["alerts"])

_alert_store: dict[UUID, AlertEvent] = {}


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


@router.get("", response_model=list[AlertEvent])
async def list_alerts() -> list[AlertEvent]:
    _seed_alerts()
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
