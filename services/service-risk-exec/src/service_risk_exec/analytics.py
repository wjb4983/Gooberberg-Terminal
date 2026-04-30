"""Incremental execution analytics with periodic reconciliation support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import sqrt


@dataclass(frozen=True)
class ExecutionAnalyticsEvent:
    event_id: str
    ts: datetime
    symbol: str
    strategy: str
    side: str
    qty: float
    price: float
    mark_price: float
    expected_price: float
    predicted_edge: float
    realized_edge: float
    confidence: float
    fees: float
    slippage: float
    latency_queue_ms: float
    latency_risk_ms: float
    latency_route_ms: float
    latency_venue_ms: float


@dataclass
class ExecutionAnalyticsStore:
    events: list[ExecutionAnalyticsEvent] = field(default_factory=list)
    notional_traded: float = 0.0
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    symbol_exposure: dict[str, float] = field(default_factory=dict)
    total_fees: float = 0.0
    total_slippage: float = 0.0
    pnl_total: float = 0.0
    wins: int = 0
    losses: int = 0
    confidence_error_sum: float = 0.0
    mae_sum: float = 0.0
    mfe_sum: float = 0.0
    _equity_curve: list[tuple[datetime, float]] = field(default_factory=list)

    def update_incremental(self, event: ExecutionAnalyticsEvent) -> None:
        self.events.append(event)
        direction = 1.0 if event.side.lower() == "buy" else -1.0
        signed_notional = direction * event.qty * event.price
        self.notional_traded += abs(event.qty * event.price)
        self.symbol_exposure[event.symbol] = self.symbol_exposure.get(event.symbol, 0.0) + signed_notional
        self.gross_exposure = sum(abs(v) for v in self.symbol_exposure.values())
        self.net_exposure = sum(self.symbol_exposure.values())
        self.total_fees += event.fees
        self.total_slippage += event.slippage
        trade_pnl = event.realized_edge * event.qty - event.fees - event.slippage
        self.pnl_total += trade_pnl
        if trade_pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
        outcome = 1.0 if trade_pnl >= 0 else 0.0
        self.confidence_error_sum += (event.confidence - outcome) ** 2
        self.mae_sum += min(0.0, (event.mark_price - event.price) * direction)
        self.mfe_sum += max(0.0, (event.mark_price - event.price) * direction)
        self._equity_curve.append((event.ts, self.pnl_total))

    def reconcile_full(self) -> None:
        events = list(self.events)
        self.__dict__.update(ExecutionAnalyticsStore(events=[]).__dict__)
        for event in sorted(events, key=lambda e: e.ts):
            self.update_incremental(event)

    def metrics_snapshot(self) -> dict[str, object]:
        n = max(len(self.events), 1)
        dd = _drawdown(self._equity_curve)
        pnl_by = _pnl_attribution(self.events)
        latency = _latency_breakdown(self.events)
        concentration = max((abs(v) for v in self.symbol_exposure.values()), default=0.0)
        turnover = self.notional_traded / max(self.gross_exposure, 1.0)
        return {
            "pnl_attribution": pnl_by,
            "drawdown": dd,
            "exposure": {
                "gross": self.gross_exposure,
                "net": self.net_exposure,
                "concentration": concentration / max(self.gross_exposure, 1.0),
            },
            "turnover": turnover,
            "latency_stage_breakdown_ms": latency,
            "decision_quality": {
                "hit_rate": self.wins / max(self.wins + self.losses, 1),
                "expectancy": self.pnl_total / max(self.wins + self.losses, 1),
                "calibration_rmse": sqrt(self.confidence_error_sum / n),
                "mae_avg": self.mae_sum / n,
                "mfe_avg": self.mfe_sum / n,
            },
        }


def _pnl_attribution(events: list[ExecutionAnalyticsEvent]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for e in events:
        pnl = e.realized_edge * e.qty - e.fees - e.slippage
        key = f"{e.symbol}|{e.strategy}|{e.side}|{e.ts.isoformat()}"
        result[key] = {"pnl": pnl, "fees": e.fees, "slippage": e.slippage}
    return result


def _drawdown(curve: list[tuple[datetime, float]]) -> dict[str, float | int | None]:
    peak = float("-inf")
    peak_ts: datetime | None = None
    trough_ts: datetime | None = None
    max_dd = 0.0
    recovery = 0
    for i, (ts, value) in enumerate(curve):
        if value > peak:
            peak = value
            peak_ts = ts
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
            trough_ts = ts
            recovery = 0
        elif trough_ts is not None and value >= peak:
            recovery = i
    duration = 0 if peak_ts is None or trough_ts is None else int((trough_ts - peak_ts).total_seconds())
    return {
        "depth": max_dd,
        "duration_seconds": duration,
        "recovery_index": recovery if recovery else None,
    }


def _latency_breakdown(events: list[ExecutionAnalyticsEvent]) -> dict[str, float]:
    if not events:
        return {"queue": 0.0, "risk": 0.0, "route": 0.0, "venue": 0.0, "total": 0.0}
    n = len(events)
    queue = sum(e.latency_queue_ms for e in events) / n
    risk = sum(e.latency_risk_ms for e in events) / n
    route = sum(e.latency_route_ms for e in events) / n
    venue = sum(e.latency_venue_ms for e in events) / n
    return {"queue": queue, "risk": risk, "route": route, "venue": venue, "total": queue + risk + route + venue}
