from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_training_run_service
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.training_runs import Service as TrainingRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.schemas import TrainingRunCreateRequest, TrainingRunResponse

router = APIRouter(prefix="/training-runs", tags=["training-runs"])


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_training_run(
    payload: TrainingRunCreateRequest,
    request: Request,
    service: TrainingRunService = Depends(get_training_run_service),
) -> TrainingRunResponse:
    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())

    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "model_config_id": str(payload.model_config_id),
            "dataset_id": payload.dataset_id,
            "parameters": payload.parameters,
            "status": "queued",
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="training",
        run_id=run_id,
        run_type="training",
        payload={"run_id": str(run_id), **payload.model_dump(mode="json")},
        queued_at=accepted_at,
    )
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="training run accepted by api-control-plane",
        run_id=run_id,
        run_type="training",
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(queued_event)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)
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
