from datetime import UTC, datetime

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from gb_core.risk import RiskExecutionAuthority
from gb_core.schemas import ExecutionDecision, RiskOverride

router = APIRouter(prefix="/risk", tags=["risk"])

authority = RiskExecutionAuthority()


class RiskOverrideUpsertRequest(BaseModel):
    strategy_key: str | None = None
    symbol: str | None = None
    max_quantity: float | None = Field(default=None, gt=0)
    max_notional: float | None = Field(default=None, gt=0)
    reason: str | None = None
    created_by: str = Field(default="api")


@router.get("/overrides", response_model=list[RiskOverride])
async def list_risk_overrides() -> list[RiskOverride]:
    return authority.list_overrides()


@router.post("/overrides", response_model=RiskOverride, status_code=status.HTTP_201_CREATED)
async def upsert_risk_override(payload: RiskOverrideUpsertRequest) -> RiskOverride:
    override = RiskOverride(
        strategy_key=payload.strategy_key,
        symbol=payload.symbol,
        max_quantity=payload.max_quantity,
        max_notional=payload.max_notional,
        reason=payload.reason,
        created_by=payload.created_by,
        created_at=datetime.now(UTC),
    )
    return authority.add_override(override)


@router.get("/decisions/recent", response_model=list[ExecutionDecision])
async def list_recent_decisions(limit: int = Query(default=50, ge=1, le=200)) -> list[ExecutionDecision]:
    return authority.recent_decisions(limit=limit)
