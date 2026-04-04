from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_backtest_run_service
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.backtest_runs import Service as BacktestRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.schemas import BacktestRunCreateRequest, BacktestRunResponse

router = APIRouter(prefix="/backtest-runs", tags=["backtest-runs"])


@router.post("", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
async def create_backtest_run(
    payload: BacktestRunCreateRequest,
    request: Request,
    service: BacktestRunService = Depends(get_backtest_run_service),
) -> BacktestRunResponse:
    run_id = uuid4()
    job_id = uuid4()
    accepted_at = datetime.now(UTC)
    trace_id = request_id_ctx_var.get() or str(uuid4())
    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "strategy_key": payload.strategy_key,
            "model_config_id": str(payload.model_config_id) if payload.model_config_id else None,
            "window_start": payload.window_start,
            "window_end": payload.window_end,
            "parameters": payload.parameters,
            "status": "queued",
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="backtest",
        run_id=run_id,
        run_type="backtest",
        payload={"run_id": str(run_id), **payload.model_dump(mode="json")},
        queued_at=accepted_at,
    )
    queued_event = JobLifecycleEvent(
        job_id=job_id,
        trace_id=trace_id,
        status=JobStatus.QUEUED,
        detail="backtest run accepted by api-control-plane",
        run_id=run_id,
        run_type="backtest",
        progress_pct=0.0,
        message="queued",
        updated_at=accepted_at,
    )
    job_state_store.upsert(queued_event)
    request.app.state.job_event_repository.persist_event(queued_event)
    await request.app.state.job_queue.enqueue(envelope)
    await _broadcast_job_event(queued_event)

    return BacktestRunResponse.model_validate(created)


@router.get("", response_model=list[BacktestRunResponse])
def list_backtest_runs(service: BacktestRunService = Depends(get_backtest_run_service)) -> list[BacktestRunResponse]:
    return [BacktestRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest_run(run_id: UUID, service: BacktestRunService = Depends(get_backtest_run_service)) -> BacktestRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest run not found")
    return BacktestRunResponse.model_validate(run)
