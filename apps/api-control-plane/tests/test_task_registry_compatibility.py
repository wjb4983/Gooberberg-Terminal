import pytest

from app.domain.task_registry import TaskRegistry
from app.schemas.training_runs import TrainingRunCreateRequest


@pytest.mark.parametrize(
    ("task_type", "subtask_type", "expected_bundle"),
    [
        ("time_series_momentum", "ranking", ("ic", "rank_ic", "hit_rate")),
        ("cross_sectional", "return_forecast", ("rmse", "mae", "r2")),
        ("cross_sectional", "allocation", ("sharpe", "sortino", "max_drawdown")),
        ("volatility", "vol_forecast", ("qlike", "rmse", "mae")),
        ("regime_switching", "regime_state", ("accuracy", "macro_f1", "log_loss")),
    ],
)
def test_resolves_default_metric_bundle(task_type: str, subtask_type: str, expected_bundle: tuple[str, ...]) -> None:
    registry = TaskRegistry()

    bundle = registry.resolve_default_metric_bundle(task_type=task_type, subtask_type=subtask_type)

    assert bundle == expected_bundle


@pytest.mark.parametrize(
    ("task_type", "subtask_type", "allowed_subtasks_hint"),
    [
        ("volatility", "ranking", "vol_forecast"),
        ("cross_sectional", "regime_state", "ranking, return_forecast, allocation"),
        ("time_series_momentum", "return_forecast", "ranking, entry_signal, exit_signal"),
    ],
)
def test_rejects_incompatible_task_subtask_with_clear_guidance(
    task_type: str,
    subtask_type: str,
    allowed_subtasks_hint: str,
) -> None:
    with pytest.raises(ValueError, match=allowed_subtasks_hint):
        TrainingRunCreateRequest(
            task_type=task_type,
            subtask_type=subtask_type,
            model_config_id="00000000-0000-0000-0000-000000000001",
            dataset_id="dataset-1",
        )
