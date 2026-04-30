from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class AlertLifecycleType(StrEnum):
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class AlertEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service: str = Field(min_length=1)
    level: AlertSeverity
    trace_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    category: str = Field(min_length=1)
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: datetime | None = None


class AlertAcknowledgeResponse(BaseModel):
    alert: AlertEvent
    detail: str


class AlertLifecycleEvent(BaseModel):
    alert_id: UUID
    event_type: AlertLifecycleType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    service: str = Field(min_length=1)
    level: LogLevel
    trace_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    category: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)


class WebSocketContractEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    seq: int = Field(ge=1)
    topic: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0"
    envelope_version: str = "1.0"
    contract_name: str = "gb.ws.event"
    contract_version: str = "1.0"
