from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas import ParameterSweepCreateRequest, ParameterSweepResponse

router = APIRouter(prefix="/parameter-sweeps", tags=["parameter-sweeps"])

_sweeps: dict[UUID, ParameterSweepResponse] = {}


@router.post("", response_model=ParameterSweepResponse, status_code=status.HTTP_201_CREATED)
def create_parameter_sweep(payload: ParameterSweepCreateRequest) -> ParameterSweepResponse:
    sweep = ParameterSweepResponse(
        id=uuid4(),
        model_config_id=payload.model_config_id,
        objective=payload.objective,
        search_space=payload.search_space,
        status="queued",
        created_at=datetime.now(UTC),
    )
    _sweeps[sweep.id] = sweep
    return sweep


@router.get("", response_model=list[ParameterSweepResponse])
def list_parameter_sweeps() -> list[ParameterSweepResponse]:
    return sorted(_sweeps.values(), key=lambda item: item.created_at, reverse=True)


@router.get("/{sweep_id}", response_model=ParameterSweepResponse)
def get_parameter_sweep(sweep_id: UUID) -> ParameterSweepResponse:
    sweep = _sweeps.get(sweep_id)
    if sweep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parameter sweep not found")
    return sweep
