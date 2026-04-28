import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_job_runner_service
from app.api.routers.ws import manager as ws_manager
from app.core.logging import request_id_ctx_var
from app.domain.job_runner import JobRunnerService
from app.domain.training_runs.constraints import apply_constraints_to_metrics
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store, job_submission_store
from app.persistence.models import BacktestRunRow, ParameterSweepRunRow, TestingRunRow, TrainingRunRow
from app.persistence.repositories import RunSqlRepository
from app.schemas import JobCreateRequest, JobLifecycleUpdateRequest, JobResponse, JobStatusResponse
from app.schemas.jobs import JOB_CANCELABLE_STATES, JOB_RETRYABLE_STATES
from app.schemas import ArtifactDetailResponse, ArtifactSummaryResponse
from app.schemas.run_constraints import extract_constraints_from_parameters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _resolve_run_constraints(request: Request, *, run_id: UUID, run_type: str):
    with request.app.state.database.session_factory() as session:
        mapping = {
            "training": TrainingRunRow,
            "backtest": BacktestRunRow,
            "testing": TestingRunRow,
        }
        model = mapping.get(run_type)
        if model is None:
            return None
        row = session.get(model, str(run_id))
        if row is None:
            return None
        return extract_constraints_from_parameters(dict(row.parameters or {}))


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
    if event.run_type == "backtest":
        await ws_manager.publish_topic(
            topic="backtests",
            payload={**payload, "run_id": str(event.run_id) if event.run_id else None},
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
    job_submission_store.upsert(envelope)
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


def _resolve_retry_envelope(job_id: UUID, request: Request) -> JobEnvelope | None:
    stored_envelope = job_submission_store.get(job_id)
    if stored_envelope is not None:
        return stored_envelope

    latest_event = job_state_store.get(job_id) or request.app.state.job_event_repository.get_latest_event(job_id)
    if latest_event is None or latest_event.run_type != "training" or latest_event.run_id is None:
        return None

    with request.app.state.database.session_factory() as session:
        training_run_row = session.get(TrainingRunRow, str(latest_event.run_id))
        if training_run_row is None:
            return None
        return JobEnvelope(
            job_id=job_id,
            trace_id=latest_event.trace_id,
            job_type="training",
            run_id=latest_event.run_id,
            run_type="training",
            payload={
                "run_id": str(latest_event.run_id),
                "model_config_id": training_run_row.model_config_id,
                "dataset_id": training_run_row.dataset_id,
                "parameters": dict(training_run_row.parameters or {}),
            },
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
    """Persist a worker lifecycle update, rebroadcast it, and sync run status."""
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
        constraints = _resolve_run_constraints(request, run_id=event.run_id, run_type=event.run_type)
        request.app.state.job_event_repository.persist_artifact_summary(
            run_id=event.run_id,
            run_type=event.run_type,
            job_id=job_id,
            artifact_ref=event.result_ref,
            checksum=event_update.artifact_checksum,
            size_bytes=event_update.artifact_size_bytes,
            metrics=apply_constraints_to_metrics(metrics=event_update.metrics, constraints=constraints),
            notes=event_update.notes,
            retention_class=event_update.artifact_retention_class,
        )
        request.app.state.job_event_repository.run_retention_jobs(
            intermediate_retention_days=request.app.state.settings.artifact_intermediate_retention_days
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


@router.get("/{job_id}/artifacts", response_model=list[ArtifactSummaryResponse])
async def list_job_artifacts(job_id: UUID, request: Request) -> list[ArtifactSummaryResponse]:
    summaries = request.app.state.job_event_repository.list_artifact_summaries(job_id)
    return [ArtifactSummaryResponse.model_validate(item) for item in summaries]


@router.get("/{job_id}/artifacts/{artifact_id}", response_model=ArtifactDetailResponse)
async def get_job_artifact_detail(job_id: UUID, artifact_id: int, request: Request) -> ArtifactDetailResponse:
    detail = request.app.state.job_event_repository.get_artifact_detail(job_id=job_id, artifact_id=artifact_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact not found")
    return ArtifactDetailResponse.model_validate(detail)


@router.post("/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_job(job_id: UUID, request: Request) -> JobStatusResponse:
    existing = job_state_store.get(job_id)
    if existing is None:
        existing = request.app.state.job_event_repository.get_latest_event(job_id)
        if existing:
            job_state_store.upsert(existing)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if existing.status not in JOB_CANCELABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"job cannot be cancelled from state '{existing.status.value}'",
        )

    cancelled_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=existing.trace_id,
        status=JobStatus.CANCELLED,
        detail="job cancelled by operator",
        run_id=existing.run_id,
        run_type=existing.run_type,
        progress_pct=existing.progress_pct,
        message="cancelled",
        result_ref=existing.result_ref,
        updated_at=datetime.now(UTC),
    )
    job_state_store.upsert(cancelled_event)
    request.app.state.job_event_repository.persist_event(cancelled_event)
    await _broadcast_job_event(cancelled_event)

    if cancelled_event.run_id and cancelled_event.run_type:
        with request.app.state.database.session_factory() as session:
            mapping = {
                "training": TrainingRunRow,
                "parameter_sweep": ParameterSweepRunRow,
                "backtest": BacktestRunRow,
            }
            model = mapping.get(cancelled_event.run_type)
            if model:
                RunSqlRepository(session, model).update_status(cancelled_event.run_id, cancelled_event.status.value)

    return JobStatusResponse(
        id=cancelled_event.job_id,
        status=cancelled_event.status,
        detail=cancelled_event.detail,
        trace_id=cancelled_event.trace_id,
        run_id=cancelled_event.run_id,
        run_type=cancelled_event.run_type,
        progress_pct=cancelled_event.progress_pct,
        message=cancelled_event.message,
        result_ref=cancelled_event.result_ref,
        updated_at=cancelled_event.updated_at,
    )


@router.post("/{job_id}/retry", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: UUID,
    request: Request,
    job_runner_service: JobRunnerService = Depends(get_job_runner_service),
) -> JobStatusResponse:
    existing = job_state_store.get(job_id)
    if existing is None:
        existing = request.app.state.job_event_repository.get_latest_event(job_id)
        if existing:
            job_state_store.upsert(existing)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    if existing.status not in JOB_RETRYABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"job cannot be retried from state '{existing.status.value}'",
        )

    prior_envelope = _resolve_retry_envelope(job_id, request)
    if prior_envelope is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="job provenance not available for retry; submit a new run manually",
        )

    trace_id = request_id_ctx_var.get() or str(uuid4())
    retry_job_id = uuid4()
    accepted_at = datetime.now(UTC)
    retry_envelope = JobEnvelope(
        job_id=retry_job_id,
        trace_id=trace_id,
        job_type=prior_envelope.job_type,
        payload=prior_envelope.payload,
        run_id=prior_envelope.run_id,
        run_type=prior_envelope.run_type,
        queued_at=accepted_at,
    )

    try:
        job_runner_service.submit(retry_envelope)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    retry_event = JobLifecycleEvent(
        job_id=retry_job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail=f"retry requested for prior job {job_id}",
        run_id=prior_envelope.run_id,
        run_type=prior_envelope.run_type,
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(retry_event)
    job_submission_store.upsert(retry_envelope)
    request.app.state.job_event_repository.persist_event(retry_event)
    await request.app.state.job_queue.enqueue(retry_envelope)
    await _broadcast_job_event(retry_event)

    if retry_event.run_id and retry_event.run_type:
        with request.app.state.database.session_factory() as session:
            mapping = {
                "training": TrainingRunRow,
                "parameter_sweep": ParameterSweepRunRow,
                "backtest": BacktestRunRow,
            }
            model = mapping.get(retry_event.run_type)
            if model:
                RunSqlRepository(session, model).update_status(retry_event.run_id, retry_event.status.value)

    return JobStatusResponse(
        id=retry_event.job_id,
        status=retry_event.status,
        detail=retry_event.detail,
        trace_id=retry_event.trace_id,
        run_id=retry_event.run_id,
        run_type=retry_event.run_type,
        progress_pct=retry_event.progress_pct,
        message=retry_event.message,
        result_ref=retry_event.result_ref,
        updated_at=retry_event.updated_at,
    )
