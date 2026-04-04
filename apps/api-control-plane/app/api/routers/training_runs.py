from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_training_run_service
from app.domain.training_runs import Service as TrainingRunService
from app.schemas import TrainingRunCreateRequest, TrainingRunResponse

router = APIRouter(prefix="/training-runs", tags=["training-runs"])


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
def create_training_run(
    payload: TrainingRunCreateRequest,
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    created = service.create(
        {
            "id": str(uuid4()),
            "model_config_id": str(payload.model_config_id),
            "dataset_id": payload.dataset_id,
            "parameters": payload.parameters,
            "status": "queued",
            "created_at": datetime.now(UTC),
        }
    )
    return TrainingRunResponse.model_validate(created)


@router.get("", response_model=list[TrainingRunResponse])
def list_training_runs(service: TrainingRunService = Depends(get_training_run_service)) -> list[TrainingRunResponse]:
    return [TrainingRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=TrainingRunResponse)
def get_training_run(run_id: UUID, service: TrainingRunService = Depends(get_training_run_service)) -> TrainingRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="training run not found")
    return TrainingRunResponse.model_validate(run)
