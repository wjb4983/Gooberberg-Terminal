from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class GuardAction(StrEnum):
    NONE = "none"
    BLOCK_NEW_ORDERS = "block_new_orders"
    DE_RISK = "de_risk"


@dataclass(frozen=True)
class StrategyRiskLimits:
    max_intraday_drawdown: float
    max_position_concentration: float
    max_daily_turnover: float
    max_slippage_deviation_bps: float


@dataclass
class StrategyGuardState:
    cumulative_turnover: float = 0.0
    cumulative_slippage_deviation_bps: float = 0.0
    total_orders: int = 0
    active: bool = True


@dataclass(frozen=True)
class GuardDecision:
    action: GuardAction
    breached_rules: list[str] = field(default_factory=list)


class RuntimeRiskGuard:
    def __init__(self, limits_by_strategy: dict[str, StrategyRiskLimits]) -> None:
        self._limits_by_strategy = limits_by_strategy
        self._state_by_strategy: dict[str, StrategyGuardState] = {}

    @classmethod
    def from_config(cls, payload: dict[str, object]) -> RuntimeRiskGuard:
        parsed: dict[str, StrategyRiskLimits] = {}
        for strategy, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            parsed[str(strategy)] = StrategyRiskLimits(
                max_intraday_drawdown=float(raw.get("max_intraday_drawdown", 1.0)),
                max_position_concentration=float(raw.get("max_position_concentration", 1.0)),
                max_daily_turnover=float(raw.get("max_daily_turnover", 1e9)),
                max_slippage_deviation_bps=float(raw.get("max_slippage_deviation_bps", 1e9)),
            )
        return cls(parsed)

    def evaluate(
        self,
        *,
        strategy_key: str,
        intraday_drawdown: float,
        position_concentration: float,
        turnover_delta: float,
        slippage_deviation_bps: float,
    ) -> GuardDecision:
        limits = self._limits_by_strategy.get(strategy_key)
        if limits is None:
            return GuardDecision(action=GuardAction.NONE)

        state = self._state_by_strategy.setdefault(strategy_key, StrategyGuardState())
        state.cumulative_turnover += max(turnover_delta, 0.0)
        state.cumulative_slippage_deviation_bps += abs(slippage_deviation_bps)
        state.total_orders += 1

        breaches: list[str] = []
        if intraday_drawdown > limits.max_intraday_drawdown:
            breaches.append("MAX_INTRADAY_DRAWDOWN")
        if position_concentration > limits.max_position_concentration:
            breaches.append("MAX_POSITION_CONCENTRATION")
        if state.cumulative_turnover > limits.max_daily_turnover:
            breaches.append("MAX_DAILY_TURNOVER")
        avg_slippage_dev = state.cumulative_slippage_deviation_bps / max(state.total_orders, 1)
        if avg_slippage_dev > limits.max_slippage_deviation_bps:
            breaches.append("MAX_SLIPPAGE_DEVIATION")

        if not breaches:
            return GuardDecision(action=GuardAction.NONE)

        if "MAX_INTRADAY_DRAWDOWN" in breaches:
            state.active = False
            return GuardDecision(action=GuardAction.DE_RISK, breached_rules=breaches)

        return GuardDecision(action=GuardAction.BLOCK_NEW_ORDERS, breached_rules=breaches)
