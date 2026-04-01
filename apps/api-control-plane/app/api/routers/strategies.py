import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.routers.risk import authority as risk_authority
from app.api.routers.ws import manager as ws_manager
from app.schemas import (
    StrategyInstance,
    StrategyInstanceActionResponse,
    StrategyInstanceCreateRequest,
    StrategyInstanceStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/strategies", tags=["strategies"])

_instances: dict[UUID, StrategyInstance] = {}


async def _broadcast_strategy_event(instance: StrategyInstance, action: str, detail: str) -> None:
    await ws_manager.publish_topic(
        topic="strategy",
        payload={
            "instance_id": str(instance.id),
            "strategy_key": instance.strategy_key,
            "mode": instance.mode.value,
            "status": instance.status.value,
            "action": action,
            "detail": detail,
            "updated_at": instance.updated_at.isoformat(),
        },
    )


@router.get("/instances", response_model=list[StrategyInstance])
async def list_strategy_instances() -> list[StrategyInstance]:
    return sorted(_instances.values(), key=lambda item: item.created_at, reverse=True)


@router.post(
    "/instances",
    response_model=StrategyInstance,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy_instance(payload: StrategyInstanceCreateRequest) -> StrategyInstance:
    timestamp = datetime.now(UTC)
    payload.intent.strategy_key = payload.strategy_key
    instance = StrategyInstance(
        strategy_key=payload.strategy_key,
        mode=payload.mode,
        intent=payload.intent,
        status=StrategyInstanceStatus.CREATED,
        created_at=timestamp,
        updated_at=timestamp,
    )
    instance.intent.strategy_instance_id = instance.id
    _instances[instance.id] = instance
    await _broadcast_strategy_event(instance, action="create", detail="strategy instance created")
    return instance


@router.post("/instances/{instance_id}/start", response_model=StrategyInstanceActionResponse)
async def start_strategy_instance(instance_id: UUID) -> StrategyInstanceActionResponse:
    instance = _instances.get(instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy instance not found")

    if instance.status == StrategyInstanceStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="strategy instance is already running",
        )

    risk_decision = risk_authority.consume_intent(instance.intent)
    if not risk_decision.approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"risk rejected intent: {risk_decision.reason_code}",
        )

    timestamp = datetime.now(UTC)
    instance.status = StrategyInstanceStatus.RUNNING
    instance.started_at = timestamp
    instance.stopped_at = None
    instance.updated_at = timestamp

    detail = f"strategy instance started with risk decision {risk_decision.decision_id}"
    await _broadcast_strategy_event(instance, action="start", detail=detail)
    return StrategyInstanceActionResponse(instance=instance, detail=detail)


@router.post("/instances/{instance_id}/stop", response_model=StrategyInstanceActionResponse)
async def stop_strategy_instance(instance_id: UUID) -> StrategyInstanceActionResponse:
    instance = _instances.get(instance_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="strategy instance not found")

    if instance.status != StrategyInstanceStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="strategy instance is not running",
        )

    timestamp = datetime.now(UTC)
    instance.status = StrategyInstanceStatus.STOPPED
    instance.stopped_at = timestamp
    instance.updated_at = timestamp

    detail = "strategy instance stopped"
    await _broadcast_strategy_event(instance, action="stop", detail=detail)
    return StrategyInstanceActionResponse(instance=instance, detail=detail)
