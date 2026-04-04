from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas import BacktestRunCreateRequest, BacktestRunResponse

router = APIRouter(prefix="/backtest-runs", tags=["backtest-runs"])

_runs: dict[UUID, BacktestRunResponse] = {}


@router.post("", response_model=BacktestRunResponse, status_code=status.HTTP_201_CREATED)
def create_backtest_run(payload: BacktestRunCreateRequest) -> BacktestRunResponse:
    run = BacktestRunResponse(
        id=uuid4(),
        strategy_key=payload.strategy_key,
        model_config_id=payload.model_config_id,
        window_start=payload.window_start,
        window_end=payload.window_end,
        parameters=payload.parameters,
        status="queued",
        created_at=datetime.now(UTC),
    )
    _runs[run.id] = run
    return run


@router.get("", response_model=list[BacktestRunResponse])
def list_backtest_runs() -> list[BacktestRunResponse]:
    return sorted(_runs.values(), key=lambda item: item.created_at, reverse=True)


@router.get("/{run_id}", response_model=BacktestRunResponse)
def get_backtest_run(run_id: UUID) -> BacktestRunResponse:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="backtest run not found")
    return run
