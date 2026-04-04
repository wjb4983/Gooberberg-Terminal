from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas import TrainingRunCreateRequest, TrainingRunResponse

router = APIRouter(prefix="/training-runs", tags=["training-runs"])

_runs: dict[UUID, TrainingRunResponse] = {}


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
def create_training_run(payload: TrainingRunCreateRequest) -> TrainingRunResponse:
    run = TrainingRunResponse(
        id=uuid4(),
        model_config_id=payload.model_config_id,
        dataset_id=payload.dataset_id,
        parameters=payload.parameters,
        status="queued",
        created_at=datetime.now(UTC),
    )
    _runs[run.id] = run
    return run


@router.get("", response_model=list[TrainingRunResponse])
def list_training_runs() -> list[TrainingRunResponse]:
    return sorted(_runs.values(), key=lambda item: item.created_at, reverse=True)


@router.get("/{run_id}", response_model=TrainingRunResponse)
def get_training_run(run_id: UUID) -> TrainingRunResponse:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="training run not found")
    return run
