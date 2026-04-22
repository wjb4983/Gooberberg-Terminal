from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_testing_run_service
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.testing_runs import Service as TestingRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store, job_submission_store
from app.schemas import TestingRunCreateRequest, TestingRunResponse

router = APIRouter(prefix="/testing-runs", tags=["testing-runs"])


@router.post("", response_model=TestingRunResponse, status_code=status.HTTP_201_CREATED)
async def create_testing_run(
    payload: TestingRunCreateRequest,
    request: Request,
    service: TestingRunService = Depends(get_testing_run_service),
) -> TestingRunResponse:
    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())

    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "mode": payload.mode.value,
            "target_refs": [ref.model_dump(mode="json") for ref in payload.target_refs],
            "parameters": payload.parameters,
            "result_summary": None,
            "status": "queued",
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="testing",
        run_id=run_id,
        run_type="testing",
        payload={"run_id": str(run_id), **payload.model_dump(mode="json")},
        queued_at=accepted_at,
    )
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="testing run accepted by api-control-plane",
        run_id=run_id,
        run_type="testing",
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(queued_event)
    job_submission_store.upsert(envelope)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)

    return TestingRunResponse.model_validate(created)


@router.get("", response_model=list[TestingRunResponse])
def list_testing_runs(service: TestingRunService = Depends(get_testing_run_service)) -> list[TestingRunResponse]:
    return [TestingRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=TestingRunResponse)
def get_testing_run(run_id: UUID, service: TestingRunService = Depends(get_testing_run_service)) -> TestingRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="testing run not found")
    return TestingRunResponse.model_validate(run)
