from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_parameter_sweep_service
from app.domain.parameter_sweeps import Service as ParameterSweepService
from app.schemas import ParameterSweepCreateRequest, ParameterSweepResponse

router = APIRouter(prefix="/parameter-sweeps", tags=["parameter-sweeps"])


@router.post("", response_model=ParameterSweepResponse, status_code=status.HTTP_201_CREATED)
def create_parameter_sweep(
    payload: ParameterSweepCreateRequest,
    service: ParameterSweepService = Depends(get_parameter_sweep_service),
) -> ParameterSweepResponse:
    created = service.create(
        {
            "id": str(uuid4()),
            "model_config_id": str(payload.model_config_id),
            "objective": payload.objective,
            "search_space": payload.search_space,
            "status": "queued",
            "created_at": datetime.now(UTC),
        }
    )
    return ParameterSweepResponse.model_validate(created)


@router.get("", response_model=list[ParameterSweepResponse])
def list_parameter_sweeps(
    service: ParameterSweepService = Depends(get_parameter_sweep_service),
) -> list[ParameterSweepResponse]:
    return [ParameterSweepResponse.model_validate(item) for item in service.list_all()]


@router.get("/{sweep_id}", response_model=ParameterSweepResponse)
def get_parameter_sweep(
    sweep_id: UUID,
    service: ParameterSweepService = Depends(get_parameter_sweep_service),
) -> ParameterSweepResponse:
    sweep = service.get(sweep_id)
    if sweep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="parameter sweep not found")
    return ParameterSweepResponse.model_validate(sweep)
