from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.training_runs import SubtaskType, TaskType


@dataclass(frozen=True)
class TaskDefinition:
    task_type: str
    allowed_subtasks: tuple[str, ...]
    target_schema: str


@dataclass(frozen=True)
class TaskSubtaskDefinition:
    task_type: str
    subtask_type: str
    target_schema: str
    default_metric_bundle: tuple[str, ...]


TASK_DEFINITIONS: dict[str, TaskDefinition] = {
    "time_series_momentum": TaskDefinition(
        task_type="time_series_momentum",
        allowed_subtasks=("ranking", "entry_signal", "exit_signal"),
        target_schema="timeseries.signal.v1",
    ),
    "cross_sectional": TaskDefinition(
        task_type="cross_sectional",
        allowed_subtasks=("ranking", "return_forecast", "allocation"),
        target_schema="cross_sectional.alpha.v1",
    ),
    "volatility": TaskDefinition(
        task_type="volatility",
        allowed_subtasks=("vol_forecast",),
        target_schema="volatility.forecast.v1",
    ),
    "regime_switching": TaskDefinition(
        task_type="regime_switching",
        allowed_subtasks=("regime_state", "entry_signal", "exit_signal"),
        target_schema="regime.switching.v1",
    ),
}

DEFAULT_METRIC_BUNDLES: dict[tuple[str, str], tuple[str, ...]] = {
    ("time_series_momentum", "ranking"): ("ic", "rank_ic", "hit_rate"),
    ("time_series_momentum", "entry_signal"): ("precision", "recall", "f1"),
    ("time_series_momentum", "exit_signal"): ("precision", "recall", "turnover"),
    ("cross_sectional", "ranking"): ("ic", "rank_ic", "top_decile_spread"),
    ("cross_sectional", "return_forecast"): ("rmse", "mae", "r2"),
    ("cross_sectional", "allocation"): ("sharpe", "sortino", "max_drawdown"),
    ("volatility", "vol_forecast"): ("qlike", "rmse", "mae"),
    ("regime_switching", "regime_state"): ("accuracy", "macro_f1", "log_loss"),
    ("regime_switching", "entry_signal"): ("precision", "recall", "f1"),
    ("regime_switching", "exit_signal"): ("precision", "recall", "turnover"),
}


def get_task_subtask_definition(task_type: TaskType | str, subtask_type: SubtaskType | str) -> TaskSubtaskDefinition:
    task_value = str(getattr(task_type, "value", task_type))
    subtask_value = str(getattr(subtask_type, "value", subtask_type))

    task_definition = TASK_DEFINITIONS.get(task_value)
    if task_definition is None:
        raise ValueError(f"unknown task_type '{task_value}'")

    if subtask_value not in task_definition.allowed_subtasks:
        allowed_values = ", ".join(task_definition.allowed_subtasks)
        raise ValueError(
            "incompatible task/subtask combination: "
            f"task_type '{task_value}' does not allow subtask_type '{subtask_value}'. "
            f"Allowed subtasks: {allowed_values}"
        )

    metric_bundle = DEFAULT_METRIC_BUNDLES.get((task_value, subtask_value))
    if metric_bundle is None:
        raise ValueError(
            "missing default metric bundle for task/subtask combination: "
            f"task_type '{task_value}', subtask_type '{subtask_value}'"
        )

    return TaskSubtaskDefinition(
        task_type=task_value,
        subtask_type=subtask_value,
        target_schema=task_definition.target_schema,
        default_metric_bundle=metric_bundle,
    )
