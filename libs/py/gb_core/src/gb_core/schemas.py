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
    failure_reason_codes: list[str] = Field(default_factory=list)
    detail: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    applied_override_id: UUID | None = None


class NvdaOpenDipReboundOpenWindow(BaseModel):
    start_minutes_from_open: int = Field(default=5, ge=0, le=60)
    end_minutes_from_open: int = Field(default=30, ge=1, le=120)


class NvdaOpenDipReboundDipThresholdRange(BaseModel):
    min_pct: float = Field(default=0.004, ge=0.001, le=0.03)
    max_pct: float = Field(default=0.012, ge=0.002, le=0.05)


class NvdaOpenDipReboundReboundHorizon(BaseModel):
    min_bars: int = Field(default=2, ge=1, le=20)
    max_bars: int = Field(default=8, ge=1, le=60)


class NvdaOpenDipReboundPositionSizing(BaseModel):
    max_notional_usd: float = Field(default=5_000, ge=100, le=50_000)
    max_position_pct_equity: float = Field(default=0.02, ge=0.0025, le=0.1)
    per_trade_risk_pct_equity: float = Field(default=0.0025, ge=0.0005, le=0.02)


class NvdaOpenDipReboundSafetyControls(BaseModel):
    max_daily_drawdown_pct: float = Field(default=0.01, ge=0.0025, le=0.05)
    stop_loss_pct: float = Field(default=0.006, ge=0.001, le=0.03)
    cooldown_minutes: int = Field(default=20, ge=1, le=240)
    max_trades_per_day: int = Field(default=2, ge=1, le=10)


class NvdaOpenDipReboundStrategyConfig(BaseModel):
    strategy_key: str = Field(default='nvda_open_dip_rebound')
    open_window: NvdaOpenDipReboundOpenWindow = Field(default_factory=NvdaOpenDipReboundOpenWindow)
    dip_threshold_range: NvdaOpenDipReboundDipThresholdRange = Field(default_factory=NvdaOpenDipReboundDipThresholdRange)
    rebound_horizon: NvdaOpenDipReboundReboundHorizon = Field(default_factory=NvdaOpenDipReboundReboundHorizon)
    position_sizing: NvdaOpenDipReboundPositionSizing = Field(default_factory=NvdaOpenDipReboundPositionSizing)
    safety_controls: NvdaOpenDipReboundSafetyControls = Field(default_factory=NvdaOpenDipReboundSafetyControls)


class NvdaOpenDipReboundTrainingRequest(BaseModel):
    strategy_config: NvdaOpenDipReboundStrategyConfig = Field(default_factory=NvdaOpenDipReboundStrategyConfig)
    dataset_id: str
    lookback_days: int = Field(default=120, ge=30, le=730)
    validation_split: float = Field(default=0.2, ge=0.1, le=0.4)


class NvdaOpenDipReboundModelVariantMetrics(BaseModel):
    variant_id: str
    win_rate: float = Field(ge=0, le=1)
    avg_return_pct: float = Field(ge=-0.2, le=0.2)
    sharpe: float = Field(ge=-5, le=10)
    max_drawdown_pct: float = Field(ge=0, le=0.5)
    total_trades: int = Field(ge=0, le=50_000)


class NvdaOpenDipReboundTrainingResultSummary(BaseModel):
    run_id: UUID
    selected_variant_id: str
    best_validation_sharpe: float = Field(ge=-5, le=10)
    realized_max_drawdown_pct: float = Field(ge=0, le=0.5)
    variant_metrics: list[NvdaOpenDipReboundModelVariantMetrics] = Field(default_factory=list)


class NvdaOpenDipReboundExternalLiveStatusSnapshot(BaseModel):
    strategy_instance_id: UUID
    paper_online: bool = False
    live_online: bool = False
    day_pnl_usd: float = Field(default=0, ge=-1_000_000, le=1_000_000)
    gross_exposure_usd: float = Field(default=0, ge=0, le=2_000_000)
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
