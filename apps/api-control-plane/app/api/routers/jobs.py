import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_job_runner_service
from app.core.logging import request_id_ctx_var
from app.domain.job_runner import JobRunnerService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.schemas import JobCreateRequest, JobLifecycleUpdateRequest, JobResponse, JobStatusResponse
from app.api.routers.ws import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _broadcast_job_event(event: JobLifecycleEvent) -> None:
    await ws_manager.publish_topic(
        topic="jobs",
        payload={
            "job_id": str(event.job_id),
            "trace_id": event.trace_id,
            "status": event.status.value,
            "detail": event.detail,
            "updated_at": event.updated_at.isoformat(),
            "result_ref": event.result_ref,
        },
    )

    await ws_manager.publish_topic(
        topic="logs",
        payload={
            "timestamp": event.updated_at.isoformat(),
            "service": "api-control-plane",
            "level": "info",
            "trace_id": event.trace_id,
            "message": event.detail,
            "category": "jobs",
            "fields": {"job_id": str(event.job_id), "status": event.status.value},
        },
    )


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

    logger.info(
        "job status fetched",
        extra={"job_id": str(job_id), "trace_id": event.trace_id},
    )
    return JobStatusResponse(
        id=event.job_id,
        status=event.status,
        detail=event.detail,
        trace_id=event.trace_id,
        result_ref=event.result_ref,
        updated_at=event.updated_at,
    )


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
        updated_at=datetime.now(UTC),
    )

    job_state_store.upsert(event)
    request.app.state.job_event_repository.persist_event(event)
    await _broadcast_job_event(event)

    return JobStatusResponse(
        id=event.job_id,
        status=event.status,
        detail=event.detail,
        trace_id=event.trace_id,
        result_ref=event.result_ref,
        updated_at=event.updated_at,
    )
