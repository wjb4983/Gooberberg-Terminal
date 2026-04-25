from __future__ import annotations

from typing import Any

from app.schemas.run_constraints import RunConstraints


def apply_constraints_to_metrics(*, metrics: dict[str, Any], constraints: RunConstraints | None) -> dict[str, Any]:
    normalized = dict(metrics)
    if constraints is None:
        return normalized

    bucket_penalty_bps = _resolve_slippage_bps(normalized, constraints)
    transaction_penalty_bps = constraints.transaction_cost.bps
    delay_penalty_bps = float(constraints.execution_delay.signal_to_fill_lag_steps)

    total_penalty_bps = transaction_penalty_bps + bucket_penalty_bps + delay_penalty_bps

    turnover = _as_float(normalized.get("turnover"))
    max_position_abs = _as_float(normalized.get("max_abs_position"))
    leverage = _as_float(normalized.get("realized_leverage"))

    limit_breaches: dict[str, bool] = {
        "max_turnover": constraints.limits.max_turnover is not None
        and turnover is not None
        and turnover > constraints.limits.max_turnover,
        "max_position_abs": constraints.limits.max_position_abs is not None
        and max_position_abs is not None
        and max_position_abs > constraints.limits.max_position_abs,
        "leverage_cap": constraints.limits.leverage_cap is not None
        and leverage is not None
        and leverage > constraints.limits.leverage_cap,
    }

    normalized["constraints"] = constraints.model_dump(mode="json")
    normalized["constraint_penalties"] = {
        "transaction_cost_bps": transaction_penalty_bps,
        "slippage_bps": bucket_penalty_bps,
        "execution_delay_bps": delay_penalty_bps,
        "total_bps": total_penalty_bps,
        "limit_breaches": limit_breaches,
    }

    objective_raw = _as_float(normalized.get("objective_raw"))
    if objective_raw is not None:
        normalized["objective_constrained"] = objective_raw - (total_penalty_bps / 10_000.0)

    validation_metrics = normalized.get("validation_metrics")
    if isinstance(validation_metrics, dict):
        adjusted: dict[str, Any] = {}
        for key, value in validation_metrics.items():
            value_float = _as_float(value)
            adjusted[key] = value_float - (total_penalty_bps / 10_000.0) if value_float is not None else value
        normalized["validation_metrics_constrained"] = adjusted

    return normalized


def _resolve_slippage_bps(metrics: dict[str, Any], constraints: RunConstraints) -> float:
    if not constraints.slippage_buckets:
        return 0.0

    liquidity_bucket = str(metrics.get("liquidity_bucket") or "")
    volatility_bucket = str(metrics.get("volatility_bucket") or "")
    for bucket in constraints.slippage_buckets:
        if bucket.liquidity_bucket == liquidity_bucket and bucket.volatility_bucket == volatility_bucket:
            return bucket.slippage_bps
    return constraints.slippage_buckets[0].slippage_bps


def _as_float(value: Any) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    return None

