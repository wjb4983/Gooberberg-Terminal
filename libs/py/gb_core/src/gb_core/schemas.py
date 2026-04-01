from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class StrategyIntent(BaseModel):
    intent_id: UUID = Field(default_factory=uuid4)
    strategy_instance_id: UUID | None = None
    strategy_key: str | None = None
    symbol: str | None = None
    side: OrderSide | None = None
    quantity: float | None = Field(default=None, gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    notes: str | None = None
    trace_id: UUID = Field(default_factory=uuid4)
    confidence: float = Field(default=0.5, ge=0, le=1)
    params: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RiskOverride(BaseModel):
    override_id: UUID = Field(default_factory=uuid4)
    strategy_key: str | None = None
    symbol: str | None = None
    max_quantity: float | None = Field(default=None, gt=0)
    max_notional: float | None = Field(default=None, gt=0)
    reason: str | None = None
    created_by: str = Field(default="system")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    intent_id: UUID
    approved: bool
    reason_code: str
    detail: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    applied_override_id: UUID | None = None
