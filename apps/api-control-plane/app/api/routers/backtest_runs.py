from datetime import UTC, datetime
import hashlib
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.dependencies import (
    get_backtest_run_service,
    get_market_data_service,
    get_model_config_service,
)
from app.api.routers.jobs import _broadcast_job_event
from app.core.logging import request_id_ctx_var
from app.domain.backtest_runs import Service as BacktestRunService
from app.domain.market_data import Service as MarketDataService
from app.domain.model_configs.compatibility import (
    resolve_dataset_compatibility,
    validate_model_dataset_compatibility,
)
from app.domain.model_configs.service import ModelConfigService
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
            "run_id": str(run_id),
            "scenario_id": "baseline",
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
    return BacktestPagedResponse(
        items=page, offset=safe_offset, limit=safe_limit, next_offset=next_offset
    )


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
    model_config_service: ModelConfigService = Depends(get_model_config_service),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> BacktestRunResponse:
    if not service.validate_confirmation_token(payload.model_dump(), payload.confirmation_token):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run estimate exceeds threshold; preflight and provide confirmation_token",
        )

    if payload.model_config_id is not None:
        model_config = model_config_service.get(payload.model_config_id)
        if model_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="model config not found"
            )

        dataset_id = payload.parameters.get("dataset_id")
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="dataset metadata is required for compatibility checks; provide parameters.dataset_id",
            )

        dataset = market_data_service.lookup_dataset(dataset_id)
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
    resolved_config = {
        "strategy_key": payload.strategy_key,
        "window_start": payload.window_start.isoformat(),
        "window_end": payload.window_end.isoformat(),
        "parameters": payload.parameters,
        "deterministic_mode": payload.deterministic_mode,
        "scenario_id": payload.scenario_id,
    }
    config_hash = hashlib.sha256(
        json.dumps(resolved_config, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    run_checksum = hashlib.sha256(
        json.dumps(
            {
                "inputs": resolved_config,
                "fills": [str(run_id), payload.scenario_id],
                "pnl": [payload.strategy_key, payload.random_seed],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    created = service.create(
        {
            "id": str(run_id),
            "job_id": str(job_id),
            "strategy_key": payload.strategy_key,
            "model_config_id": str(payload.model_config_id) if payload.model_config_id else None,
            "window_start": payload.window_start,
            "window_end": payload.window_end,
            "parameters": payload.parameters,
            "deterministic_mode": payload.deterministic_mode,
            "scenario_id": payload.scenario_id,
            "status": "queued",
            "git_sha": payload.git_sha,
            "config_hash": config_hash,
            "data_snapshot_id": payload.data_snapshot_id,
            "random_seed": payload.random_seed,
            "engine_version": payload.engine_version,
            "feature_set_version": payload.feature_set_version,
            "timezone": payload.timezone,
            "calendar_id": payload.calendar_id,
            "resolved_config": resolved_config,
            "environment_fingerprint": payload.environment_fingerprint,
            "run_checksum": run_checksum,
            "created_at": accepted_at,
        }
    )

    envelope = JobEnvelope(
        job_id=job_id,
        trace_id=trace_id,
        job_type="backtest",
        run_id=run_id,
        run_type="backtest",
        payload={
            "run_id": str(run_id),
            **payload.model_dump(mode="json", exclude={"confirmation_token"}),
        },
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
def list_backtest_runs(
    service: BacktestRunService = Depends(get_backtest_run_service),
) -> list[BacktestRunResponse]:
    return [BacktestRunResponse.model_validate(item) for item in service.list_all()]


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest_run(
    run_id: UUID, service: BacktestRunService = Depends(get_backtest_run_service)
) -> BacktestRunResponse:
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest run not found")
    return BacktestRunResponse.model_validate(run)


@router.get("/{run_id}/status", response_model=BacktestStatusResponse)
def get_backtest_status(
    run_id: UUID, service: BacktestRunService = Depends(get_backtest_run_service)
) -> BacktestStatusResponse:
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
def list_backtest_events(
    run_id: UUID, offset: int = Query(default=0), limit: int = Query(default=100)
) -> BacktestPagedResponse:
    return _paginate(_seeded_rows("event", run_id, 2_000), offset, limit)


@router.get("/{run_id}/trades", response_model=BacktestPagedResponse)
def list_backtest_trades(
    run_id: UUID, offset: int = Query(default=0), limit: int = Query(default=100)
) -> BacktestPagedResponse:
    return _paginate(_seeded_rows("trade", run_id, 5_000), offset, limit)


@router.get("/{run_id}/metrics")
def get_backtest_metrics(run_id: UUID) -> dict[str, object]:
    return {
        "run_id": str(run_id),
        "scenario_id": "baseline",
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
