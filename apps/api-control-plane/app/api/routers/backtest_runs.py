from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import get_backtest_run_service
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.backtest_runs import Service as BacktestRunService
from app.jobs.models import JobEnvelope, JobLifecycleEvent, JobStatus
from app.jobs.store import job_state_store
from app.schemas import (
    BacktestPagedResponse,
    BacktestRunCreateRequest,
    BacktestRunPreflightRequest,
    BacktestRunPreflightResponse,
    BacktestRunResponse,
    BacktestStatusResponse,
)

router = APIRouter(prefix="/backtest-runs", tags=["backtest-runs"])


def _seeded_rows(prefix: str, run_id: UUID, total: int) -> list[dict[str, object]]:
    base = run_id.hex
    return [
        {
            "id": f"{prefix}-{index}",
            "timestamp": datetime.now(UTC).isoformat(),
            "detail": f"{prefix} detail {index} for run {base[:8]}",
            "value": round(((index * 13) % 97) / 10, 2),
        }
        for index in range(total)
    ]


def _paginate(items: list[dict[str, object]], offset: int, limit: int) -> BacktestPagedResponse:
    safe_offset = max(offset, 0)
    safe_limit = min(max(limit, 1), 200)
    page = items[safe_offset : safe_offset + safe_limit]
    next_offset = safe_offset + safe_limit if safe_offset + safe_limit < len(items) else None
    return BacktestPagedResponse(items=page, offset=safe_offset, limit=safe_limit, next_offset=next_offset)


@router.post("/preflight", response_model=BacktestRunPreflightResponse)
def estimate_backtest_run(
    payload: BacktestRunPreflightRequest,
    service: BacktestRunService = Depends(get_backtest_run_service),
) -> BacktestRunPreflightResponse:
    estimate = service.estimate_run_size(payload.model_dump())
    return BacktestRunPreflightResponse.model_validate(estimate)


@router.post("", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
async def create_backtest_run(
    payload: BacktestRunCreateRequest,
    request: Request,
    service: BacktestRunService = Depends(get_backtest_run_service),
) -> BacktestRunResponse:
    if not service.validate_confirmation_token(payload.model_dump(), payload.confirmation_token):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run estimate exceeds threshold; preflight and provide confirmation_token",
        )

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
        payload={"run_id": str(run_id), **payload.model_dump(mode="json", exclude={"confirmation_token"})},
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


@router.get("/{run_id}/status", response_model=BacktestStatusResponse)
def get_backtest_status(run_id: UUID, service: BacktestRunService = Depends(get_backtest_run_service)) -> BacktestStatusResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest run not found")
    return BacktestStatusResponse(
        run_id=UUID(str(run["id"])),
        job_id=UUID(str(run["job_id"])),
        status=run["status"],
        summary=f"{run['status']}: strategy={run['strategy_key']}",
        updated_at=run["created_at"],
    )


@router.get("/{run_id}/events", response_model=BacktestPagedResponse)
def list_backtest_events(run_id: UUID, offset: int = Query(default=0), limit: int = Query(default=100)) -> BacktestPagedResponse:
    return _paginate(_seeded_rows("event", run_id, 2_000), offset, limit)


@router.get("/{run_id}/trades", response_model=BacktestPagedResponse)
def list_backtest_trades(run_id: UUID, offset: int = Query(default=0), limit: int = Query(default=100)) -> BacktestPagedResponse:
    return _paginate(_seeded_rows("trade", run_id, 5_000), offset, limit)


@router.get("/{run_id}/metrics")
def get_backtest_metrics(run_id: UUID) -> dict[str, object]:
    return {
        "run_id": str(run_id),
        "metrics": {
            "sharpe": 1.42,
            "max_drawdown_pct": 8.7,
            "cagr_pct": 12.3,
            "win_rate_pct": 57.1,
        },
    }


@router.get("/{run_id}/equity-refs")
def list_backtest_equity_refs(run_id: UUID) -> dict[str, object]:
    return {
        "run_id": str(run_id),
        "refs": [
            f"s3://simulated-equity/{run_id}/curve.parquet",
            f"s3://simulated-equity/{run_id}/drawdown.parquet",
        ],
    }
