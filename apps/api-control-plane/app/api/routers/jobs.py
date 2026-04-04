import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_job_runner_service
from app.api.routers.ws import manager as ws_manager
from app.core.logging import request_id_ctx_var
from app.domain.job_runner import JobRunnerService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.persistence.models import BacktestRunRow, ParameterSweepRunRow, TrainingRunRow
from app.persistence.repositories import RunSqlRepository
from app.schemas import JobCreateRequest, JobLifecycleUpdateRequest, JobResponse, JobStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _broadcast_job_event(event: JobLifecycleEvent) -> None:
    payload = {
        "job_id": str(event.job_id),
        "run_id": str(event.run_id) if event.run_id else None,
        "status": event.status.value,
        "progress_pct": event.progress_pct,
        "message": event.message or event.detail,
        "timestamp": event.updated_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
    }
    await ws_manager.publish_topic(topic="jobs", payload=payload)
    await ws_manager.publish_topic(topic="logs", payload=payload)


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    job_request: JobCreateRequest,
    request: Request,
    job_runner_service: JobRunnerService = Depends(get_job_runner_service),
) -> JobResponse:
    trace_id = request_id_ctx_var.get() or str(uuid4())
    job_id = uuid4()
    accepted_at = datetime.now(UTC)

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type=job_request.job_type,
        payload=job_request.payload,
        run_id=job_request.run_id,
        run_type=job_request.run_type,
        queued_at=accepted_at,
    )
    try:
        job_runner_service.submit(envelope)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="job accepted by api-control-plane",
        run_id=job_request.run_id,
        run_type=job_request.run_type,
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )

    job_state_store.upsert(queued_event)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)

    logger.info("job accepted", extra={"job_id": str(job_id), "trace_id": trace_id})
    return JobResponse(
        id=job_id,
        job_type=job_request.job_type,
        status=JobStatus.QUEUED,
        payload=job_request.payload,
        trace_id=trace_id,
        run_id=job_request.run_id,
        run_type=job_request.run_type,
        accepted_at=accepted_at,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: UUID, request: Request) -> JobStatusResponse:
    event = job_state_store.get(job_id)
    if event is None:
        event = request.app.state.job_event_repository.get_latest_event(job_id)
        if event:
            job_state_store.upsert(event)

    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    return JobStatusResponse(
        id=event.job_id,
        status=event.status,
        detail=event.detail,
        trace_id=event.trace_id,
        run_id=event.run_id,
        run_type=event.run_type,
        progress_pct=event.progress_pct,
        message=event.message,
        result_ref=event.result_ref,
        updated_at=event.updated_at,
    )


@router.get("/{job_id}/events", response_model=list[JobStatusResponse])
async def list_job_events(job_id: UUID, request: Request) -> list[JobStatusResponse]:
    events = request.app.state.job_event_repository.list_events(job_id)
    return [
        JobStatusResponse(
            id=event.job_id,
            status=event.status,
            detail=event.detail,
            trace_id=event.trace_id,
            run_id=event.run_id,
            run_type=event.run_type,
            progress_pct=event.progress_pct,
            message=event.message,
            result_ref=event.result_ref,
            updated_at=event.updated_at,
        )
        for event in events
    ]


@router.post("/{job_id}/events", response_model=JobStatusResponse)
async def publish_job_event(
    job_id: UUID,
    event_update: JobLifecycleUpdateRequest,
    request: Request,
) -> JobStatusResponse:
    existing = job_state_store.get(job_id)
    if existing is None:
        existing = request.app.state.job_event_repository.get_latest_event(job_id)

    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=existing.trace_id,
        status=event_update.status,
        detail=event_update.detail,
        run_id=event_update.run_id or existing.run_id,
        run_type=event_update.run_type or existing.run_type,
        progress_pct=event_update.progress_pct,
        message=event_update.message,
        result_ref=event_update.result_ref,
        updated_at=datetime.now(UTC),
    )

    job_state_store.upsert(event)
    request.app.state.job_event_repository.persist_event(event)
    await _broadcast_job_event(event)

    run_id = event.run_id
    run_type = event.run_type
    if run_id and run_type:
        with request.app.state.database.session_factory() as session:
            mapping = {
                "training": TrainingRunRow,
                "parameter_sweep": ParameterSweepRunRow,
                "backtest": BacktestRunRow,
            }
            model = mapping.get(run_type)
            if model:
                RunSqlRepository(session, model).update_status(run_id, event.status.value)

    if event.status in {JobStatus.SUCCESS, JobStatus.FAILED} and event.run_id and event.run_type and event.result_ref:
        request.app.state.job_event_repository.persist_artifact_summary(
            run_id=event.run_id,
            run_type=event.run_type,
            job_id=job_id,
            artifact_ref=event.result_ref,
            metrics=event_update.metrics,
            notes=event_update.notes,
        )

    return JobStatusResponse(
        id=event.job_id,
        status=event.status,
        detail=event.detail,
        trace_id=event.trace_id,
        run_id=event.run_id,
        run_type=event.run_type,
        progress_pct=event.progress_pct,
        message=event.message,
        result_ref=event.result_ref,
        updated_at=event.updated_at,
    )
