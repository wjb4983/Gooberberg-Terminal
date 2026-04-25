from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class TransactionCostModel(BaseModel):
    bps: float = Field(default=0.0, ge=0.0)
    per_contract_fee: float = Field(default=0.0, ge=0.0)


class SlippageBucketModel(BaseModel):
    liquidity_bucket: str = Field(min_length=1)
    volatility_bucket: str = Field(min_length=1)
    slippage_bps: float = Field(ge=0.0)


class ExecutionDelayModel(BaseModel):
    signal_to_fill_lag_steps: int = Field(default=0, ge=0)


class PositionLimitModel(BaseModel):
    max_turnover: float | None = Field(default=None, ge=0.0)
    max_position_abs: float | None = Field(default=None, ge=0.0)
    leverage_cap: float | None = Field(default=None, ge=0.0)


class RunConstraints(BaseModel):
    transaction_cost: TransactionCostModel = Field(default_factory=TransactionCostModel)
    slippage_buckets: list[SlippageBucketModel] = Field(default_factory=list)
    execution_delay: ExecutionDelayModel = Field(default_factory=ExecutionDelayModel)
    limits: PositionLimitModel = Field(default_factory=PositionLimitModel)

    @model_validator(mode="after")
    def ensure_unique_slippage_buckets(self) -> "RunConstraints":
        seen: set[tuple[str, str]] = set()
        for bucket in self.slippage_buckets:
            key = (bucket.liquidity_bucket, bucket.volatility_bucket)
            if key in seen:
                raise ValueError(
                    "slippage_buckets must not include duplicate liquidity_bucket/volatility_bucket combinations"
                )
            seen.add(key)
        return self


def attach_constraints_to_parameters(
    *, parameters: dict[str, Any], constraints: RunConstraints | None
) -> dict[str, Any]:
    normalized = dict(parameters)
    if constraints is None:
        return normalized

    metadata = dict(normalized.get("run_metadata") or {})
    metadata["constraints"] = constraints.model_dump(mode="json")
    normalized["run_metadata"] = metadata
    return normalized


def extract_constraints_from_parameters(parameters: dict[str, Any]) -> RunConstraints | None:
    run_metadata = parameters.get("run_metadata")
    if not isinstance(run_metadata, dict):
        return None
    raw_constraints = run_metadata.get("constraints")
    if not isinstance(raw_constraints, dict):
        return None
    return RunConstraints.model_validate(raw_constraints)

