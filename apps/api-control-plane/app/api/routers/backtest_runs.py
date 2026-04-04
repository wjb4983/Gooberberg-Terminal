from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_backtest_run_service
from app.domain.backtest_runs import Service as BacktestRunService
from app.schemas import BacktestRunCreateRequest, BacktestRunResponse

router = APIRouter(prefix="/backtest-runs", tags=["backtest-runs"])


@router.post("", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
def create_backtest_run(
    payload: BacktestRunCreateRequest,
    service: BacktestRunService = Depends(get_backtest_run_service),
) -> BacktestRunResponse:
    created = service.create(
        {
            "id": str(uuid4()),
            "strategy_key": payload.strategy_key,
            "model_config_id": str(payload.model_config_id) if payload.model_config_id else None,
            "window_start": payload.window_start,
            "window_end": payload.window_end,
            "parameters": payload.parameters,
            "status": "queued",
            "created_at": datetime.now(UTC),
        }
    )
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
