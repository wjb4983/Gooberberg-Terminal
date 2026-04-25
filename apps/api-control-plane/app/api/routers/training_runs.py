from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_market_data_service,
    get_model_config_service,
    get_training_run_service,
)
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.market_data import Service as MarketDataService
from app.domain.model_configs.compatibility import (
    resolve_dataset_compatibility,
    validate_model_dataset_compatibility,
)
from app.domain.model_configs.service import ModelConfigService
from app.domain.training_runs import Service as TrainingRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store, job_submission_store
from app.schemas import TrainingRunCreateRequest, TrainingRunResponse

router = APIRouter(prefix="/training-runs", tags=["training-runs"])


@router.post("", response_model=TrainingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_training_run(
    payload: TrainingRunCreateRequest,
    request: Request,
    service: TrainingRunService = Depends(get_training_run_service),
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> TrainingRunResponse:
    model_config = model_config_service.get(payload.model_config_id)
    if model_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model config not found")

    dataset = market_data_service.lookup_dataset(payload.dataset_id)
    if dataset is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="dataset not found; ingest data and retry",
        )

    model_spec = request.app.state.model_registry.require(str(model_config["model_family"]))
    dataset_profile = resolve_dataset_compatibility(dataset.metadata, dataset.timeframe)
    compatibility_errors = validate_model_dataset_compatibility(
        model_spec=model_spec, dataset_metadata=dataset_profile
    )
    if compatibility_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "model config is incompatible with dataset",
                "errors": compatibility_errors,
            },
        )

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
            "task_type": payload.task_type.value,
            "subtask_type": payload.subtask_type.value,
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
    job_submission_store.upsert(envelope)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)
    return TrainingRunResponse.model_validate(created)


@router.get("", response_model=list[TrainingRunResponse])
def list_training_runs(
    service: TrainingRunService = Depends(get_training_run_service),
) -> list[TrainingRunResponse]:
    return [TrainingRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=TrainingRunResponse)
def get_training_run(
    run_id: UUID, service: TrainingRunService = Depends(get_training_run_service)
) -> TrainingRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="training run not found")
    return TrainingRunResponse.model_validate(run)
