from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_parameter_sweep_service
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.parameter_sweeps import Service as ParameterSweepService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.schemas import ParameterSweepCreateRequest, ParameterSweepResponse

router = APIRouter(prefix="/parameter-sweeps", tags=["parameter-sweeps"])


@router.post("", response_model=ParameterSweepResponse, status_code=status.HTTP_201_CREATED)
async def create_parameter_sweep(
    payload: ParameterSweepCreateRequest,
    request: Request,
    service: ParameterSweepService = Depends(get_parameter_sweep_service),
) -> ParameterSweepResponse:
    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())
    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "model_config_id": str(payload.model_config_id),
            "parameter_set_id": str(payload.parameter_set_id) if payload.parameter_set_id else None,
            "objective": payload.objective,
            "search_space": payload.search_space,
            "provenance_snapshot": payload.provenance_snapshot,
            "status": "queued",
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="parameter_sweep",
        run_id=run_id,
        run_type="parameter_sweep",
        payload={"run_id": str(run_id), **payload.model_dump(mode="json")},
        queued_at=accepted_at,
    )
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="parameter sweep accepted by api-control-plane",
        run_id=run_id,
        run_type="parameter_sweep",
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(queued_event)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)

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
