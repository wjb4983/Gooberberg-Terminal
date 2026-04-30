from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: UUID
    trace_id: UUID
    schema_version: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    event_time: datetime
    ingest_time: datetime
    process_time: datetime
    producer: str = Field(min_length=1)
    strategy_version: str = Field(min_length=1)
    config_hash: str = Field(min_length=1)


class MarketDataEvent(BaseEvent):
    event_type: Literal["MarketDataEvent"]
    symbol: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    last: float = Field(gt=0)
    volume: float = Field(ge=0)


class SignalEvent(BaseEvent):
    event_type: Literal["SignalEvent"]
    signal_name: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    strength: float = Field(ge=-1, le=1)
    features: dict[str, float] = Field(default_factory=dict)


class DecisionEvent(BaseEvent):
    event_type: Literal["DecisionEvent"]
    decision: Literal["buy", "sell", "hold"]
    symbol: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class OrderIntentEvent(BaseEvent):
    event_type: Literal["OrderIntentEvent"]
    intent_id: UUID = Field(default_factory=uuid4)
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    limit_price: float | None = Field(default=None, gt=0)


class RiskCheckEvent(BaseEvent):
    event_type: Literal["RiskCheckEvent"]
    intent_id: UUID
    passed: bool
    reason: str = Field(min_length=1)
    max_notional: float = Field(gt=0)


class OrderEvent(BaseEvent):
    event_type: Literal["OrderEvent"]
    order_id: UUID = Field(default_factory=uuid4)
    intent_id: UUID
    status: Literal["accepted", "rejected", "sent", "cancelled"]
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)


class FillEvent(BaseEvent):
    event_type: Literal["FillEvent"]
    order_id: UUID
    fill_id: UUID = Field(default_factory=uuid4)
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class PositionEvent(BaseEvent):
    event_type: Literal["PositionEvent"]
    symbol: str = Field(min_length=1)
    net_qty: float
    avg_price: float = Field(ge=0)
    market_value: float


class PnLEvent(BaseEvent):
    event_type: Literal["PnLEvent"]
    symbol: str = Field(min_length=1)
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float


class AlertEvent(BaseEvent):
    event_type: Literal["AlertEvent"]
    severity: Literal["info", "warning", "critical"]
    message: str = Field(min_length=1)
    category: str = Field(min_length=1)


class HeartbeatEvent(BaseEvent):
    event_type: Literal["HeartbeatEvent"]
    service: str = Field(min_length=1)
    status: Literal["ok", "degraded", "down"]


EVENT_MODELS: dict[str, type[BaseEvent]] = {
    model.__name__: model
    for model in (
        MarketDataEvent,
        SignalEvent,
        DecisionEvent,
        OrderIntentEvent,
        RiskCheckEvent,
        OrderEvent,
        FillEvent,
        PositionEvent,
        PnLEvent,
        AlertEvent,
        HeartbeatEvent,
    )
}


def json_schema_definitions() -> dict[str, dict[str, Any]]:
    return {name: model.model_json_schema() for name, model in EVENT_MODELS.items()}


def avro_schema_definitions() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for name, model in EVENT_MODELS.items():
        fields: list[dict[str, Any]] = []
        for field_name, field in model.model_fields.items():
            if field_name == "event_type":
                fields.append({"name": field_name, "type": "string", "default": name})
                continue
            fields.append({"name": field_name, "type": "string"})
        schemas[name] = {
            "type": "record",
            "name": name,
            "namespace": "gb.events",
            "fields": fields,
        }
    return schemas


def protobuf_schema_definitions() -> dict[str, str]:
    proto: dict[str, str] = {}
    for name, model in EVENT_MODELS.items():
        lines = ["syntax = \"proto3\";", "", f"message {name} {{"]
        for idx, field_name in enumerate(model.model_fields, start=1):
            lines.append(f"  string {field_name} = {idx};")
        lines.append("}")
        proto[name] = "\n".join(lines)
    return proto


def validate_ingestion_payload(event_name: str, payload: dict[str, Any]) -> BaseEvent:
    model = EVENT_MODELS[event_name]
    return model.model_validate(payload)


def utc_now() -> datetime:
    return datetime.now(UTC)
